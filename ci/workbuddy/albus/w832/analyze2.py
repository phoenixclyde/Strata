#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""W832 第二轮分析：噪声底盘 + 生成长度一致性 + 每臂离散度。"""
import json, statistics as st, collections, io

P = "D:/workbuddy_space/strata_ws/albus/w832/results.jsonl"
recs = [json.loads(l) for l in io.open(P, encoding="utf-8") if l.strip() and "tok_per_ms" in l]
print("n =", len(recs))

print("\n=== 每臂离散度（tok/ms） ===")
print("%-11s %-5s %8s %8s %8s %8s %7s" % ("axis", "val", "min", "median", "max", "max/min", "spread%"))
g = collections.defaultdict(list)
for r in recs:
    g[(r["axis"], r["value"])].append(r["tok_per_ms"])
for k in sorted(g):
    v = sorted(g[k])
    print("%-11s %-5.2f %8.4f %8.4f %8.4f %8.2f %7.1f"
          % (k[0], k[1], v[0], st.median(v), v[-1], v[-1] / v[0], 100 * (v[-1] / v[0] - 1)))

print("\n=== 生成长度（completion）与窗口数 ===")
comp = collections.Counter(r["completion"] for r in recs)
print("  completion 取值分布:", dict(comp))
win = [r["windows"] for r in recs]
print("  windows: min %s median %s max %s" % (min(win), st.median(win), max(win)))

print("\n=== 逐条明细（按 axis 排序） ===")
print("%-11s %-5s %-3s %5s %6s %7s %7s %8s" % ("axis", "val", "b", "comp", "win", "tok/win", "ms/win", "tok/ms"))
for r in sorted(recs, key=lambda x: (x["axis"], x["block"], x["value"])):
    print("%-11s %-5.2f %-3d %5s %6s %7.2f %7.2f %8.4f"
          % (r["axis"], r["value"], r["block"], r["completion"], r["windows"],
             r["tok_per_win"], r["ms_per_win"], r["tok_per_ms"]))
