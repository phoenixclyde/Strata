#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Repair the four-part report's first table: restore 3-column 3a/3b rows.

Regression window: W1038..W1042. Before W1038 the rows were
  | 3a | args (19 flag) | ... |
  | 3b | env (9 keys)   | ... |
From W1038 they became two-column rows
  | 3a args 明细 | ... |
GFM pads a missing trailing cell with an EMPTY one, so the "值" column renders
blank and the long middle cell blows the table width out. Verified by rendering
with python-markdown 3.11.3 (albus/w1043/render_check.py).
"""
import io
import os
import sys

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
ROUNDS = ["w1038", "w1039", "w1040", "w1041", "w1042"]


def fix_line(line):
    for tag, label in (("3a", "args 明细"), ("3b", "env 明细")):
        pref = "| %s %s | " % (tag, label)
        if line.startswith(pref) and line.rstrip().endswith("|"):
            body = line[len(pref):]
            return "| %s | %s | %s" % (tag, label, body)
    return line


def main():
    changed = 0
    for r in ROUNDS:
        p = os.path.join(ROOT, "albus", r, "reply.md")
        lines = io.open(p, encoding="utf-8").read().splitlines()
        out = [fix_line(l) for l in lines]
        n = sum(1 for a, b in zip(lines, out) if a != b)
        if n:
            io.open(p, "w", encoding="utf-8", newline="\n").write("\n".join(out) + "\n")
        print("%-8s fixed %d row(s)" % (r, n))
        changed += n
    print("TOTAL fixed rows: %d" % changed)
    return 0 if changed == 10 else 1


if __name__ == "__main__":
    sys.exit(main())
