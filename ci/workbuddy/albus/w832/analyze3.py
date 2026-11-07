#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""W832：逐块配对差 + 符号检验 + 结论口径。"""
import json, statistics as st, collections, io

P = "D:/workbuddy_space/strata_ws/albus/w832/results.jsonl"
recs = [json.loads(l) for l in io.open(P, encoding="utf-8") if l.strip() and "tok_per_ms" in l]
BASE = {"spec_min_p": 0.70, "pcie_frac": 0.20}

for axis in ("spec_min_p", "pcie_frac"):
    rows = [r for r in recs if r["axis"] == axis]
    byblock = collections.defaultdict(dict)
    for r in rows:
        byblock[r["block"]][r["value"]] = r
    base = BASE[axis]
    print("=" * 70)
    print("AXIS", axis, " base =", base)
    print("block | " + " | ".join("%7.2f" % v for v in sorted({r["value"] for r in rows})))
    for b in sorted(byblock):
        m = byblock[b]
        print("  b%-3d | " % b + " | ".join("%7.4f" % m[v]["tok_per_ms"] for v in sorted(m)))
    print()
    for v in sorted({r["value"] for r in rows}):
        if v == base:
            continue
        d = [byblock[b][v]["tok_per_ms"] - byblock[b][base]["tok_per_ms"]
             for b in sorted(byblock) if v in byblock[b] and base in byblock[b]]
        neg = sum(1 for x in d if x < 0)
        print("  %-5.2f vs base: Δ 中位 %+0.4f (%+.1f%%)  为负 %d/%d  范围 %+0.4f..%+0.4f"
              % (v, st.median(d), 100 * st.median(d) / byblock[sorted(byblock)[0]][base]["tok_per_ms"],
                 neg, len(d), min(d), max(d)))
    print()

print("=" * 70)
sp = collections.defaultdict(list)
for r in recs:
    sp[(r["axis"], r["value"])].append(r["tok_per_ms"])
allspread = [100 * (max(v) / min(v) - 1) for v in sp.values()]
print("噪声底盘：每臂 max/min 离散 = %.1f%% .. %.1f%%（中位 %.1f%%）"
      % (min(allspread), max(allspread), st.median(allspread)))
print("⇒ 任何 < %.1f%% 的效应，在这个设计下都不可分辨" % st.median(allspread))
