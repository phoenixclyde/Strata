#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Audit every Markdown table in the workspace for structural emptiness.

Why: the owner said "第一张是空表" about the four-part report. A previous ad-hoc
scan used a heredoc regex that the local shell shim mangled (self-test False),
so this file is written to disk first and executed as a real .py file.

Checks per table block:
  T0 header/separator column count must match (GFM: mismatch => NOT a table)
  T1 at least one data row
  T2 every data row has a non-empty "value" cell
  T3 column counts of data rows must not exceed header (extra pipes break rows)
"""
import io
import os
import re
import sys

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
SEP = re.compile(r"^\s*\|?\s*:?-{1,}:?\s*(\|\s*:?-{1,}:?\s*)*\|?\s*$")


def cells(line):
    s = line.strip()
    # escaped pipes inside a cell are not separators
    s = s.replace("\\|", "\x00")
    if s.startswith("|"):
        s = s[1:]
    if s.endswith("|"):
        s = s[:-1]
    return [c.strip().replace("\x00", "\\|") for c in s.split("|")]


def blocks_of(lines):
    i = 0
    while i < len(lines):
        if lines[i].strip().startswith("|"):
            j = i
            while j < len(lines) and lines[j].strip().startswith("|"):
                j += 1
            yield i + 1, lines[i:j]
            i = j
        else:
            i += 1


def audit(path):
    lines = io.open(path, encoding="utf-8", errors="replace").read().splitlines()
    out = []
    for start, blk in blocks_of(lines):
        hdr = cells(blk[0])
        sep_ok = len(blk) > 1 and bool(SEP.match(blk[1]))
        nsep = len(cells(blk[1])) if len(blk) > 1 else 0
        data = blk[2:] if sep_ok else blk[1:]
        problems = []
        if not sep_ok:
            problems.append("T0-no-separator")
        elif nsep != len(hdr):
            problems.append("T0-col-mismatch(header=%d,sep=%d)" % (len(hdr), nsep))
        if not data:
            problems.append("T1-no-data-row")
        empty_val = 0
        over = 0
        for r in data:
            c = cells(r)
            if len(c) < 2 or not any(c[1:]):
                empty_val += 1
            if len(c) > len(hdr):
                over += 1
        if empty_val:
            problems.append("T2-empty-value-rows=%d" % empty_val)
        if over:
            problems.append("T3-overwide-rows=%d" % over)
        out.append((start, len(hdr), len(data), problems, blk[0][:78]))
    return out


def main():
    targets = []
    for base, dirs, files in os.walk(os.path.join(ROOT, "albus")):
        for f in files:
            if f.lower().endswith(".md"):
                targets.append(os.path.join(base, f))
    for f in os.listdir(os.path.join(ROOT, "deploy")):
        if f.lower().endswith(".md"):
            targets.append(os.path.join(ROOT, "deploy", f))
    targets.sort()
    bad = 0
    for p in targets:
        rel = os.path.relpath(p, ROOT).replace("\\", "/")
        for start, ncol, ndata, probs, head in audit(p):
            if probs:
                bad += 1
                print("%-46s L%-5d cols=%-2d data=%-3d %-52s %s"
                      % (rel, start, ncol, ndata, ",".join(probs), head))
    print("\nTOTAL suspicious tables: %d / %d md files" % (bad, len(targets)))
    print("\n=== four-part reports (first table only) ===")
    for r in ["w1039", "w1040", "w1041", "w1042"]:
        p = os.path.join(ROOT, "albus", r, "reply.md")
        if not os.path.isfile(p):
            print(r, "MISSING")
            continue
        a = audit(p)
        if a:
            s, ncol, ndata, probs, head = a[0]
            print("%s first table at L%d: cols=%d data_rows=%d problems=%s"
                  % (r, s, ncol, ndata, probs or "none"))
    return 0


if __name__ == "__main__":
    sys.exit(main())
