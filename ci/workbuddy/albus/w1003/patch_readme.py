#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""README 补记 W1003 的镜像门（在 166 上执行）。"""
import io
import subprocess

P = "/home/albus/strata166/pr/strata-fork/ci/README.md"
s = open(P, encoding="utf-8").read()

old_row = "| round closing (laptop) | `albus/w1002/round_close.py` | `report_lint` FAIL, `plan_lint` FAIL, missing four-section report |"
new_row = ("| round closing (laptop) | `albus/w1002/round_close.py` | `report_lint` FAIL, `plan_lint` FAIL, "
           "missing four-section report, authoritative plan drifted from the 166 mirror |")
assert old_row in s, "row anchor not found"
s = s.replace(old_row, new_row, 1)

anchor = "Negative self-tests are mandatory:"
note = (
    "**A tool pointed at the wrong copy is not a gate either (W1003).** `plan_lint` reads the laptop's\n"
    "`deploy/W832_OPT_PLAN_V2.md`. The 166 copy of that same file had not changed since 2026-11-03 02:54 —\n"
    "18 rounds (W882-W1002) of write-backs existed only on the laptop, and nothing compared the two, so the\n"
    "gate stayed green against a file nobody on the box was reading. `albus/w1003/mirror_check.py` now\n"
    "compares both files byte for byte over ssh; `round_close.py` treats a mismatch as a hard failure and\n"
    "`--sync` pushes the laptop copy (now the primary) leaving a dated `.bak` on 166. The comparator has its\n"
    "own negative self-test: a forged all-zero remote hash must be reported as DRIFT.\n\n")
assert anchor in s
s = s.replace(anchor, note + anchor, 1)

open(P, "w", encoding="utf-8", newline="\n").write(s)
print("README patched:", len(s), "chars")
