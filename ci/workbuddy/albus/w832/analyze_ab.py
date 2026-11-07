#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""W832 P0-b 分析：从原始 jsonl 行比较 0.1.53 与 0.1.54n2（同镜像、同配置、只差 exe）。"""
import json, statistics as st, collections, io, sys

P = sys.argv[1] if len(sys.argv) > 1 else "D:/workbuddy_space/strata_ws/albus/w832/ab_engine.out"
recs = []
for line in io.open(P, encoding="utf-8", errors="replace"):
    line = line.strip()
    if line.startswith("{"):
        try:
            recs.append(json.loads(line))
        except Exception:
            pass

print("records:", len(recs))
arms = sorted({r["arm"] for r in recs})
print("arms:", arms)

# decode
print("\n=== decode（5 × 128 tok，T=0） ===")
print("%-9s %6s %9s %9s %9s" % ("arm", "n", "gen_tps", "gen_ms", "median"))
dec = collections.defaultdict(list)
for r in recs:
    if r.get("note") == "decode" and r.get("gen_tps"):
        dec[r["arm"]].append(r)
for a in arms:
    g = dec.get(a, [])
    if not g:
        print("%-9s   0  (无数据)" % a)
        continue
    tps = [x["gen_tps"] for x in g]
    ms = [x["gen_ms"] for x in g]
    print("%-9s %6d %9.2f %9.0f %9.2f  %s"
          % (a, len(g), st.median(tps), st.median(ms), st.median(tps),
             " ".join("%.1f" % x for x in tps)))
if len(arms) == 2 and all(dec.get(a) for a in arms):
    a, b = arms
    da = st.median([x["gen_tps"] for x in dec[a]])
    db = st.median([x["gen_tps"] for x in dec[b]])
    print("  → %s vs %s: %+.1f%%（%s 为基准）" % (b, a, 100 * (db / da - 1), a))

# read
print("\n=== read（3 档 × 2 次，max_tokens=1） ===")
print("%-9s %8s %8s %9s %8s %7s" % ("arm", "approx", "tokens", "read_ms", "read_tps", "reused"))
rd = collections.defaultdict(list)
for r in recs:
    if str(r.get("note", "")).startswith("read") and r.get("read_ms"):
        rd[(r["arm"], r["note"])].append(r)
for a in arms:
    for note in ("read1300", "read2500", "read4500"):
        g = rd.get((a, note), [])
        if not g:
            continue
        print("%-9s %8s %8.0f %9.0f %8.1f %7.0f"
              % (a, note.replace("read", ""), st.median([x["prompt_tokens"] for x in g]),
                 st.median([x["read_ms"] for x in g]), st.median([x["read_tps"] for x in g]),
                 st.median([x["reused"] for x in g])))

print("\n=== 同长度对比（read_ms，越小越好；只有 reused≈0 的样本计入） ===")
for note in ("read1300", "read2500", "read4500"):
    vals = {}
    for a in arms:
        g = [x for x in rd.get((a, note), []) if x.get("reused", 0) < 5]
        if g:
            vals[a] = st.median([x["read_ms"] for x in g])
    if len(vals) == 2:
        a, b = arms
        print("  %-9s %s=%d ms, %s=%d ms  → %+.1f%%" % (note, a, vals[a], b, vals[b],
                                                        100 * (vals[b] / vals[a] - 1)))
    elif vals:
        print("  %-9s 只有一侧数据: %s" % (note, vals))
