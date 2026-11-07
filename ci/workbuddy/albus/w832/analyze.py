#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""W832 P0-a 分析：按声明判据 tokens/win ÷ ms/win 排序 + 块内配对差。

块内配对是关键：每个块里每个取值都出现一次，块内漂移对消，
配对差的中位数比跨臂均值更能扛住整机漂移。
"""
import json, statistics as st, collections, sys, io

P = sys.argv[1] if len(sys.argv) > 1 else "D:/workbuddy_space/strata_ws/albus/w832/results.jsonl"
recs = [json.loads(l) for l in io.open(P, encoding="utf-8") if l.strip()]
recs = [r for r in recs if r.get("tok_per_ms")]
print("records with timing:", len(recs), "/", len([1 for _ in io.open(P, encoding='utf-8') if _.strip()]))

BASE = {"spec_min_p": 0.70, "pcie_frac": 0.20}

for axis in ("spec_min_p", "pcie_frac"):
    rows = [r for r in recs if r["axis"] == axis]
    if not rows:
        continue
    print("\n" + "=" * 78)
    print("AXIS", axis, " (base = %s)" % BASE[axis])
    print("%-8s %5s %8s %9s %9s %9s %8s" % ("value", "n", "tok/ms", "ms/win", "tok/win", "avgT", "wall t/s"))
    groups = collections.defaultdict(list)
    for r in rows:
        groups[r["value"]].append(r)
    base_val = BASE[axis]
    for v in sorted(groups):
        g = groups[v]
        med = lambda k: st.median([x[k] for x in g if x.get(k) is not None])
        print("%-8.2f %5d %8.4f %9.2f %9.2f %9.2f %8.2f"
              % (v, len(g), med("tok_per_ms"), med("ms_per_win"), med("tok_per_win"),
                 med("avg_t"), med("wall_tps")))

    # 块内配对
    byblock = collections.defaultdict(dict)
    for r in rows:
        byblock[r["block"]][r["value"]] = r
    print("\n  块内配对（相对 base，正数=比 base 快）")
    for v in sorted(groups):
        if v == base_val:
            continue
        d_tok, d_ms = [], []
        for b, m in sorted(byblock.items()):
            if v in m and base_val in m:
                d_tok.append(m[v]["tok_per_ms"] - m[base_val]["tok_per_ms"])
                d_ms.append(m[v]["ms_per_win"] - m[base_val]["ms_per_win"])
        if d_tok:
            print("   %-6.2f vs %.2f : Δtok/ms %+0.4f (n=%d, 范围 %+0.4f..%+0.4f)  Δms/win %+0.2f"
                  % (v, base_val, st.median(d_tok), len(d_tok), min(d_tok), max(d_tok),
                     st.median(d_ms)))

# 输出一致性（贪心 + 精确投机 ⇒ 各臂答案应逐字相同）
shas = collections.Counter(r["sha"] for r in recs)
print("\n" + "=" * 78)
print("答案一致性：不同 sha 数 =", len(shas), " 众数占比 = %.1f%%"
      % (100.0 * shas.most_common(1)[0][1] / len(recs)))
if len(shas) > 1:
    for s, c in shas.most_common(5):
        vals = sorted({(r["axis"], r["value"]) for r in recs if r["sha"] == s})
        print("   sha %s x%d  出现在 %s" % (s, c, vals))
