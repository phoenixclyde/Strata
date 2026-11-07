#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""审计索引必须点名每一个存在的审计件（本机侧门）。

W1006 起因：`AUDIT_INDEX.md` 是回答「哪些轮次还没审」的唯一依据，而它的覆盖表停在 AUDIT24，
`AUDIT25_W952_W985.md` 已经在 deploy/ 里躺了一天。**边界由产物推导，不能手工维护在旁边**——
与 W832 镜像（W1003）、方案里同一数字的三处副本（W1005）是同一种病。

  python tools/audit_index.py
  python tools/audit_index.py --self-test
"""
import io
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
DEPLOY = os.path.join(HERE, "..", "deploy")
INDEX = os.path.join(DEPLOY, "AUDIT_INDEX.md")

ART = re.compile(r"^AUDIT(\d+)_[A-Za-z0-9_]+\.md$")
ROW = re.compile(r"\|\s*\**\s*AUDIT(\d+)\s*\**\s*\|")


def check(index=INDEX, deploy=DEPLOY, quiet=False):
    fails = []
    have = set()
    for line in io.open(index, encoding="utf-8"):
        for m in ROW.finditer(line):
            have.add(int(m.group(1)))
    want = {}
    for f in os.listdir(deploy):
        m = ART.match(f)
        if m:
            want[int(m.group(1))] = f
    for n in sorted(n for n in want if n not in have):
        fails.append("AUDIT%d (%s) has no row in AUDIT_INDEX.md" % (n, want[n]))
    for n in sorted(have):
        if n not in want:
            fails.append("AUDIT_INDEX.md has a row for AUDIT%d but no AUDIT%d_*.md exists" % (n, n))
    # AUDIT27: the 合计 row must equal the sum of the graded rows, and its range must
    # equal the derived bounds.  W1007 introduced the former as a rule but never a gate.
    rows = total(index)
    src = io.open(index, encoding="utf-8").read()
    m = re.search(r"^\| \*\*合计\*\* \|(.*)$", src, re.M)
    if rows and m:
        cells = [c.strip().strip("*").strip() for c in m.group(1).strip().strip("|").split("|")]
        got = [int(c) for c in cells[1:5] if re.fullmatch(r"\d+", c)]
        want_sum = [sum(c) for c in zip(*rows)]
        if got != want_sum:
            fails.append("合计 row %s != derived sum %s" % (got, want_sum))
        lo, hi = bounds(index)
        if "W%d–W%d" % (lo, hi) not in m.group(1):
            fails.append("合计 row has a stale range (derived W%d–W%d)" % (lo, hi))
    elif not m:
        fails.append("AUDIT_INDEX.md has no 合计 row")
    if not quiet:
        if fails:
            print("AUDIT_INDEX: FAIL (%d)" % len(fails))
            for f in fails:
                print("   " + f)
        else:
            print("AUDIT_INDEX: PASS (%d audits, every artefact has a row)" % len(want))
    return fails


def total(index=INDEX):
    """Sum the P columns by reading the table.  The total is derived, never typed.

    Row shape: | AUDIT<n> | 覆盖 | P0 | P1 | P2 | P3 | 文件 |
    A '-' or a non-numeric cell means "not graded", which counts as 0.
    """
    rows = []
    for line in io.open(index, encoding="utf-8"):
        if not re.match(r"\|\s*\**\s*AUDIT\d+", line):
            continue
        cells = [c.strip().strip("*").strip() for c in line.strip().strip("|").split("|")]
        if len(cells) < 6:
            continue
        num = []
        for c in cells[2:6]:
            if re.fullmatch(r"\d+", c):
                num.append(int(c))
            elif c in ("-", "—", ""):
                num.append(0)
            else:
                num = None
                break
        if num:
            rows.append(num)
    return rows


def bounds(index=INDEX):
    """Derive the covered round range from the table itself (AUDIT27: never hardcode it).

    W1007 made the total derived from the rows, but left 'W776–W1005' as a literal in
    fix_total(): every new audit silently kept the old boundary.  Read the coverage column
    of every AUDIT row and take min/max of all W<number> tokens.
    """
    nums = []
    for line in io.open(index, encoding="utf-8"):
        if not re.match(r"\|\s*\**\s*AUDIT\d+", line):
            continue
        cells = [c.strip() for c in line.strip().strip("|").split("|")]
        if len(cells) < 2:
            continue
        nums += [int(x) for x in re.findall(r"\bW(\d{3,4})\b", cells[1])]
    return (min(nums), max(nums)) if nums else (0, 0)


def fix_total(index=INDEX):
    rows = total(index)
    tot = [sum(c) for c in zip(*rows)]
    lo, hi = bounds(index)
    src = io.open(index, encoding="utf-8").read()
    new = re.sub(r"^\| \*\*合计\*\* \|.*$",
                 "| **合计** | **W%d–W%d + 方案本体**（%d 件有 P 分级） | **%d** | **%d** | **%d** | **%d** | — |"
                 % (lo, hi, len(rows), tot[0], tot[1], tot[2], tot[3]),
                 src, count=1, flags=re.M)
    assert new != src, "no 合计 row to rewrite"
    io.open(index, "w", encoding="utf-8", newline="\n").write(new)
    print("AUDIT_INDEX: 合计 rewritten from %d rows -> %s" % (len(rows), tot))


def self_test():
    import tempfile
    ok = 0
    src = io.open(INDEX, encoding="utf-8").read()
    bad = "\n".join(l for l in src.splitlines() if "AUDIT25" not in l)
    with tempfile.NamedTemporaryFile("w", suffix=".md", encoding="utf-8", delete=False,
                                     newline="\n") as f:
        f.write(bad)
        p = f.name
    if any("AUDIT25" in x for x in check(p, quiet=True)):
        ok += 1
    else:
        print("  self-test MISS: a missing AUDIT25 row was not caught")
    with tempfile.NamedTemporaryFile("w", suffix=".md", encoding="utf-8", delete=False,
                                     newline="\n") as f:
        f.write(src + "\n| **AUDIT99** | W1-W2 | 0 | 0 | 0 | 0 | nowhere |\n")
        p2 = f.name
    if any("AUDIT99" in x for x in check(p2, quiet=True)):
        ok += 1
    else:
        print("  self-test MISS: a phantom AUDIT99 row was not caught")
    for p in (p, p2):
        os.unlink(p)
    print("SELF_TEST: %d/2" % ok)
    return 0 if ok == 2 else 1


if __name__ == "__main__":
    if "--fix-total" in sys.argv:
        fix_total()
        sys.exit(0)
    if "--self-test" in sys.argv:
        sys.exit(self_test())
    sys.exit(1 if check() else 0)
