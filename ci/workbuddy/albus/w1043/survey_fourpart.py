#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Cross-round survey of the four-part report's first table."""
import io
import os
import re
import sys

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))


def ncols(line):
    s = line.strip().replace("\\|", "\x00")
    if s.startswith("|"):
        s = s[1:]
    if s.endswith("|"):
        s = s[:-1]
    return [c.strip() for c in s.split("|")]


def first_table(path):
    lines = io.open(path, encoding="utf-8", errors="replace").read().splitlines()
    for i, l in enumerate(lines):
        if l.strip().startswith("|") and i + 1 < len(lines) and re.match(r"^\s*\|[\s:|-]+\|\s*$", lines[i + 1]):
            j = i
            while j < len(lines) and lines[j].strip().startswith("|"):
                j += 1
            return i + 1, lines[i:j]
    return None, []


def main():
    base = os.path.join(ROOT, "albus")
    rounds = sorted(d for d in os.listdir(base) if re.fullmatch(r"w\d{4}", d))
    print("%-8s %-6s %-6s %-8s %-8s %s" % ("round", "line", "rows", "data", "cols", "verdict"))
    for d in rounds:
        p = os.path.join(base, d, "reply.md")
        if not os.path.isfile(p):
            continue
        st, blk = first_table(p)
        if not blk:
            print("%-8s %-6s %-6s %-8s %-8s %s" % (d, "-", 0, 0, "-", "NO TABLE"))
            continue
        hdr = len(ncols(blk[0]))
        colset = sorted(set(len(ncols(l)) for l in blk))
        data = len(blk) - 2
        empty = sum(1 for l in blk[2:] if not any(c for c in ncols(l)[1:]))
        verdict = "OK" if data >= 10 and colset == [hdr] and empty == 0 else (
            "EMPTY" if data == 0 or empty == data else "RAGGED" if colset != [hdr] else "THIN")
        print("%-8s %-6s %-6s %-8s %-8s %s" % (d, st, len(blk), data, ",".join(map(str, colset)), verdict))
    return 0


if __name__ == "__main__":
    sys.exit(main())
