#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""指针完整性：文档里指向的「号」和「节」必须真的存在。

W1007 起因：`AUDIT_INDEX` 的「仍未结清」表里挂着 `R15'`（wait copy 的预取深度）——
**账本里没有这个号**。它既不在 `PROGRESS.tsv`，也不在方案 §6.2，所以 `plan_lint`（查有号有账）
与 `ledger_lint`（查行内字段）都看不见它：一条永久免检的待办。同一天还发现 `PROGRESS` 的备注
会写「见 §6.2 新NN」，而那个新NN 有几次是写错的/没建的。

三条判据：
  1. `R<n>'` / `P<n>'`（残值号）必须能落到账本里的一个号（基号或带撇号的行）；
  2. `PROGRESS` 备注里出现的 `§6.2 新<n>` 必须在方案里有这一行；
  3. `PROGRESS` 备注里出现的 `§6.5 回写/补记 · W<n>` 必须在方案里有这个小节。

  python tools/pointer_lint.py
  python tools/pointer_lint.py --self-test
"""
import io
import os
import re
import sys

ROOT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..")
DEPLOY = os.path.join(ROOT, "deploy")
PLAN = os.path.join(DEPLOY, "W832_OPT_PLAN_V2.md")
PROG = os.path.join(DEPLOY, "PROGRESS.tsv")


def ledger_ids():
    ids = set()
    with io.open(PROG, encoding="utf-8") as f:
        for line in f:
            if line.startswith("#") or line.count("\t") < 9:
                continue
            ids.add(line.split("\t")[1])
    return ids


def owned_residuals():
    """Primed ids a ledger row actually owns, i.e. mentions in its note (R98 owns R15')."""
    out = set()
    with io.open(PROG, encoding="utf-8") as f:
        for line in f:
            if line.startswith("#") or line.count("\t") < 9:
                continue
            out |= {m + "'" for m in re.findall(r"\b([RPX]\d{1,3})'", line)}
    return out


def check(quiet=False):
    fails = []
    ids = ledger_ids()
    owned = owned_residuals()
    plan = io.open(PLAN, encoding="utf-8").read()

    # 1. residual ids x' must resolve to a real id
    seen = set()
    SEVERITY = {"P0", "P1", "P2", "P3"}      # 审计分级，不是条目号
    # 只扫「活文档」：冻结的历史件（W713/W750/W775…）逐字保留，不参与整改
    ACTIVE = re.compile(r"^(W832_OPT_PLAN_V2|AUDIT\d+.*|SESSION_STATE|AUDIT_INDEX)\.md$")
    for fn in sorted(os.listdir(DEPLOY)):
        if not ACTIVE.match(fn):
            continue
        txt = io.open(os.path.join(DEPLOY, fn), encoding="utf-8", errors="replace").read()
        for m in re.finditer(r"\b([RPX]\d{1,3})[’']", txt):
            base = m.group(1)
            if base in SEVERITY or base in seen:
                continue
            if (base + "'") in ids or (base + "'") in owned:
                continue
            seen.add(base)
            fails.append("%s: %s' is owned by no ledger row (add %s' or name it in a note)"
                         % (fn, base, base))

    # 1b. the same scan over the ledger's own notes
    with io.open(PROG, encoding="utf-8") as f:
        for line in f:
            if line.startswith("#") or line.count("\t") < 9:
                continue
            for m in re.finditer(r"\b([RPX]\d{1,3})[’']", line):
                base = m.group(1)
                if base in SEVERITY or base in seen:
                    continue
                if (base + "'") in ids or (base + "'") in owned:
                    continue
                seen.add(base)
                fails.append("PROGRESS.tsv: %s' is owned by no ledger row" % base)

    # 2/3. pointers from the ledger's notes into the plan
    new_rows = set(re.findall(r"^\| \*\*新(\d+)\*\*", plan, re.M))
    heads = set(re.findall(r"^#{2,4} .*?回写 · (W\d+)", plan, re.M))
    heads |= set(re.findall(r"^#{2,4} .*?补记 · (W\d+)", plan, re.M))
    with io.open(PROG, encoding="utf-8") as f:
        for line in f:
            if line.startswith("#") or line.count("\t") < 9:
                continue
            c = line.split("\t")
            pid, note = c[1], c[-2]
            for n in re.findall(r"§6\.2\s*新(\d+)", note):
                if n not in new_rows:
                    fails.append("%s: note points at §6.2 新%s, which does not exist" % (pid, n))
            for w in re.findall(r"§6\.5[^·|]{0,8}·\s*(W\d+)", note):
                if w not in heads:
                    fails.append("%s: note points at §6.5 · %s, which has no section" % (pid, w))

    if not quiet:
        if fails:
            print("POINTER: FAIL (%d)" % len(fails))
            for f in fails:
                print("   " + f)
        else:
            print("POINTER: PASS (residual ids resolve, §-pointers land)")
    return fails


def self_test():
    """Plant a live-document defect and a dangling §-pointer, expect both."""
    global PROG
    import shutil
    import tempfile
    ok = 0
    tmp = os.path.join(tempfile.mkdtemp(), "AUDIT99_SELFTEST.md")
    io.open(tmp, "w", encoding="utf-8", newline="\n").write("残值 R99' 未立项。\n")
    shutil.copy(tmp, os.path.join(DEPLOY, "AUDIT99_SELFTEST.md"))
    try:
        f = check(quiet=True)
        if any("R99' is owned by no ledger row" in x for x in f):
            ok += 1
        else:
            print("  self-test MISS: a primed id in a LIVE document was not caught")
    finally:
        os.unlink(os.path.join(DEPLOY, "AUDIT99_SELFTEST.md"))
        os.unlink(tmp)

    prog_p = os.path.join(tempfile.mkdtemp(), "PROGRESS.tsv")
    shutil.copy(PROG, prog_p)
    txt = io.open(prog_p, encoding="utf-8").read().split("\n")
    for i, l in enumerate(txt):
        if l.count("\t") >= 9 and not l.startswith("#"):
            c = l.split("\t")
            c[-2] = c[-2] + " 见 §6.2 新99"
            txt[i] = "\t".join(c)
            break
    io.open(prog_p, "w", encoding="utf-8", newline="\n").write("\n".join(txt))
    old = PROG
    PROG = prog_p
    try:
        f = check(quiet=True)
        if any("新99" in x for x in f):
            ok += 1
        else:
            print("  self-test MISS: a pointer to a non-existent §6.2 row was not caught")
    finally:
        PROG = old
    print("SELF_TEST: %d/2" % ok)
    return 0 if ok == 2 else 1


if __name__ == "__main__":
    if "--self-test" in sys.argv:
        sys.exit(self_test())
    sys.exit(1 if check() else 0)
