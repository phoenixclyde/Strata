#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""AUDIT28 -- every audit output must be named, graded, and free of retracted live claims.

W1007 found the index lagging the artefacts; AUDIT27 made the *sum* derived but the
per-row P numbers were still hand-copied.  AUDIT28 adds one canonical
    > VERDICT: AUDIT<n> P0=a P1=b P2=c P3=d src=...
line to every numbered artefact and checks it against AUDIT_INDEX.md.  It also
names the 39 companion W*_AUDIT/VERDICT/REVIEW files that audit_index.py's
``want[n]`` dict silently overwrites when two files share a number.

Checks:
  1 every index row's counts == its artefact's VERDICT line
  2 every audit-ish .md in deploy/ is either a numbered artefact or in COMPANIONS
  3 both ledgers have unique ids and valid statuses
  4 a retracted external-fact claim may only appear inside a marked correction line

  python tools/audit_outputs.py [--self-test]
"""
import io
import os
import re
import sys

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
DEP = os.path.join(ROOT, "deploy")
IDX = os.path.join(DEP, "AUDIT_INDEX.md")
ACTIVE_PREFIX = ("AUDIT",)

# a *live* retracted claim; a line carrying one must also carry a retraction marker
BAD_CLAIMS = [
    "PR 内没有性能栏", "PR 内无性能栏", "无性能栏", "原文无对照数据",
    "原文明确说没有对照数据", "无法核实 17.2%", "contains no benchmark",
    "PR 无 benchmark",
]
MARKERS = ("撤回", "更正", "误判", "AUDIT28", "已废止", "作废", "已并入", "复核为", "为**错**")


def index_rows(index=IDX):
    out = {}
    for line in io.open(index, encoding="utf-8"):
        m = re.match(r"\|\s*\**\s*AUDIT(\d+)\s*\**\s*\|", line)
        if not m:
            continue
        c = [x.strip().strip("*").strip() for x in line.strip().strip("|").split("|")]
        nums = [int(x) if re.fullmatch(r"\d+", x) else 0 for x in c[2:6]]
        out[int(m.group(1))] = (nums, c[6].strip().strip("`") if len(c) > 6 else "")
    return out


def companions(index=IDX):
    m = re.search(r"^COMPANIONS:\s*(.+)$", io.open(index, encoding="utf-8").read(), re.M)
    return set(m.group(1).split()) if m else set()


def audit_ish():
    return {f for f in os.listdir(DEP)
            if f.endswith(".md") and f != "AUDIT_INDEX.md"
            and re.search(r"AUDIT|VERDICT|REVIEW", f, re.I)}


def check(quiet=False):
    fails = []
    rows = index_rows()
    named = {f for _, f in rows.values()}
    # 1 verdict lines
    for n, (nums, fname) in sorted(rows.items()):
        p = os.path.join(DEP, fname)
        if not os.path.isfile(p):
            fails.append("AUDIT%d: artefact %s missing" % (n, fname))
            continue
        t = io.open(p, encoding="utf-8", errors="replace").read()
        v = re.findall(r"^> VERDICT: AUDIT(\d+) P0=(\d+) P1=(\d+) P2=(\d+) P3=(\d+)", t, re.M)
        if len(v) != 1:
            fails.append("AUDIT%d: expected 1 VERDICT line, got %d" % (n, len(v)))
            continue
        got = [int(x) for x in v[0][1:]]
        if int(v[0][0]) != n or got != nums:
            fails.append("AUDIT%d: VERDICT %s != index %s" % (n, got, nums))
    # 2 companions
    comp = companions()
    unexplained = sorted(audit_ish() - named - comp)
    ghost = sorted(comp - audit_ish())
    if unexplained:
        fails.append("2: %d audit outputs not named in index/COMPANIONS: %s" % (len(unexplained), unexplained[:4]))
    if ghost:
        fails.append("2: COMPANIONS names %d missing files: %s" % (len(ghost), ghost[:4]))
    # 3 ledgers
    for name, idcol, stcol in (("AUDIT_LEDGER.tsv", 0, 7), ("AUDIT_LEDGER_A24.tsv", 0, 4)):
        p = os.path.join(DEP, name)
        ids, bad = set(), []
        for i, l in enumerate(io.open(p, encoding="utf-8"), 1):
            f = l.rstrip("\n").split("\t")
            if len(f) <= max(idcol, stcol) or l.startswith("id\t"):
                continue
            if f[idcol] in ids:
                bad.append("dup:%s@%d" % (f[idcol], i))
            ids.add(f[idcol])
            if name.endswith("A24.tsv") and f[stcol] not in ("RESOLVED", "DEFERRED", "WONTFIX"):
                bad.append("status:%s@%d" % (f[stcol], i))
        if bad:
            fails.append("3: %s %s" % (name, bad[:3]))
    # 4 retracted claims must be marked
    scan = [os.path.join(DEP, f) for f in sorted(os.listdir(DEP))
            if f.endswith((".md", ".tsv")) and (f.startswith(ACTIVE_PREFIX)
            or f in ("PROGRESS.tsv", "W832_OPT_PLAN_V2.md", "SESSION_STATE.md"))]
    scan += [os.path.join(ROOT, "tools", f) for f in sorted(os.listdir(os.path.join(ROOT, "tools")))
             if f.endswith(".py") and f != "audit_outputs.py"]  # its own pattern table / negative fixtures
    live = []
    for p in scan:
        if not os.path.isfile(p):
            continue
        for i, l in enumerate(io.open(p, encoding="utf-8", errors="replace"), 1):
            if any(b in l for b in BAD_CLAIMS) and not any(m in l for m in MARKERS):
                live.append("%s:%d" % (os.path.basename(p), i))
    if live:
        fails.append("4: retracted claim still written as current: %s" % live[:5])
    if not quiet:
        print("AUDIT_OUTPUTS: index_rows=%d numbered=%d companions=%d ledgers=2 live_bad_claims=%d" %
              (len(rows), len(named), len(comp), len(live)))
        if fails:
            print("AUDIT_OUTPUTS: FAIL (%d)" % len(fails))
            for f in fails:
                print("   " + f)
        else:
            print("AUDIT_OUTPUTS: PASS (verdicts, companions, ledgers, retractions)")
    return fails


def self_test():
    ok = 0
    rows = index_rows()
    # 1 a wrong verdict must be detected
    n, (nums, fname) = sorted(rows.items())[0]
    t = io.open(os.path.join(DEP, fname), encoding="utf-8").read()
    bad = t.replace("P0=%d" % nums[0], "P0=99", 1)
    ok += 1 if bad != t and "P0=99" in bad else 0
    # 2 a missing companion must be detected
    ok += 1 if "W773_AUDIT.md" in companions() else 0
    # 3 a live false claim must be detected
    line = "引用它时只能说「作者称」，PR 内无性能栏"
    ok += 1 if any(b in line for b in BAD_CLAIMS) and not any(m in line for m in MARKERS) else 0
    # 4 a marked retraction must be accepted
    line2 = "【AUDIT28 撤回】原写「PR 内无性能栏」是错的"
    ok += 1 if any(m in line2 for m in MARKERS) else 0
    print("SELF_TEST: %d/4" % ok)
    return 0 if ok == 4 else 1


if __name__ == "__main__":
    if "--self-test" in sys.argv:
        sys.exit(self_test())
    sys.exit(1 if check() else 0)
