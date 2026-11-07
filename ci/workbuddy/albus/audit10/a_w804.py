#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""AUDIT10 · W804 五臂读长扫描复算。
   两种口径并列：
     (a) 按 target 索引（每 target 3 次取中位，最干净）
     (b) 按实测 prompt_tokens 分档（文档似乎用的是这个）
   C 臂是 share=0 基线（文档把 C 列写成 0）。
"""
import re
import statistics as st
import sys

FILES = {"A": "albus/audit10/w804_read_20261026_000306.txt",
         "B": "albus/audit10/w804_read_20261026_000306.txt",
         "C": "albus/audit10/w804_read_20261026_000306.txt",
         "D": "albus/audit10/w804_read2_20261026_001144.txt",
         "E": "albus/audit10/w804_read2_20261026_001144.txt"}
DOC = {196: (-27.5, -26.1, 0, -3.1, -30.2), 608: (-22.2, -23.2, 0, -2.9, -24.3),
       891: (-21.2, -23.2, 0, -6.5, -25.0), 1095: (-0.3, -31.7, 0, -20.2, -32.6),
       1203: (-0.0, -27.3, 0, -13.7, -27.1), 1406: (-7.0, -25.6, 0, -14.3, -26.9),
       1820: (-0.6, -15.6, 0, -4.2, -16.5), 2196: (-1.0, -14.2, 0, -5.2, -14.4)}


def load():
    data = {}   # arm -> [(target, tok, wall_s)]
    for arm, path in FILES.items():
        cur = None
        for ln in open(path, encoding="utf-8", errors="replace"):
            m = re.match(r"^=== ARM (\S+)", ln)
            if m:
                cur = m.group(1); continue
            m = re.search(r"rep\d+ target=(\d+)\s+chars=\d+\s+prompt_tokens=(\d+)\s+wall=([\d.]+)s", ln)
            if m and cur == arm:
                data.setdefault(arm, []).append((int(m.group(1)), int(m.group(2)), float(m.group(3))))
    return data


d = load()
for a in sorted(d):
    print("arm %s: %d 条, targets=%s" % (a, len(d[a]), sorted({t for t, _, _ in d[a]})))

print("\n(a) 按 target 索引（3 次中位，wall 秒）：")
print("%-8s %-7s %-8s %-8s %-8s %-8s %-8s | %s" % ("target", "median", "A", "B", "C", "D", "E", "A/B/D/E 相对 C"))
tg = sorted({t for a in d for t, _, _ in d[a]})
for t in tg:
    row = {}
    for a in "ABCDE":
        xs = [w for tt, _, w in d.get(a, []) if tt == t]
        row[a] = st.median(xs) if xs else None
    toks = [k for tt, k, _ in d["A"] if tt == t]
    rel = []
    for a in "ABDE":
        rel.append("%+.1f%%" % (100 * (row[a] - row["C"]) / row["C"]) if row.get(a) and row.get("C") else "-")
    print("%-8d %-7d %-8.2f %-8.2f %-8.2f %-8.2f %-8.2f | %s"
          % (t, int(st.median(toks)), row["A"], row["B"], row["C"], row["D"], row["E"], " ".join(rel)))

print("\n(b) 按实测 read 分档（同一 read 值跨臂取中位）—— 检查文档 8 行是否可复现：")
bins = {}
for a in d:
    for t, k, w in d[a]:
        bins.setdefault(k, {}).setdefault(a, []).append(w)
print("%-7s %s" % ("read", "  ".join("%-9s" % x for x in ("A", "B", "C", "D", "E")) + " | 文档 A/B/C/D/E vs 复算"))
for k in sorted(bins):
    row = {a: st.median(v) for a, v in bins[k].items()}
    doc = DOC.get(k)
    if not row.get("C"):
        continue
    cells = []
    for a in "ABCDE":
        cells.append("%+.1f%%" % (100 * (row[a] - row["C"]) / row["C"]) if row.get(a) else "-")
    line = "%-7d %s" % (k, "  ".join("%-9s" % c for c in cells))
    if doc:
        line += " | 文档 " + "/".join("%.1f" % x for x in doc)
    print(line)
