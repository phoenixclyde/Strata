# -*- coding: utf-8 -*-
"""W803 分析 v3：off 2 样本（A,C，md5 相同）vs on 4 样本（B,D,E,F）
输出每个"对"的 KL 统计，再用「对"对"的分布」判 off-vs-on 是否落在 on-vs-on 之内。
"""
import io, itertools, json, math, os, statistics as st, sys

D = sys.argv[1] if len(sys.argv) > 1 else r"D:/workbuddy_space/strata_ws/albus/w803"
OFF, ON = ["A", "C"], ["B", "D", "E", "F"]


def load(arm):
    rows = {}
    with io.open(os.path.join(D, "w803_logpos_%s.tsv" % arm), encoding="utf-8") as f:
        for line in f:
            c = line.rstrip("\n").split("\t")
            if len(c) < 9:
                continue
            topk = {}
            for x in c[8:]:
                if ":" in x:
                    i, v = x.split(":", 1)
                    topk[int(i)] = float(v)
            rows[int(c[0])] = {"tgt": int(c[1]), "lp_tgt": float(c[2]), "top": int(c[3]),
                               "is_top": int(c[5]), "topk": topk}
    return rows


def kl(P, Q):
    sp, sq = set(P["topk"]), set(Q["topk"])
    if not sp or not sq:
        return None
    pp = {t: math.exp(P["topk"][t]) for t in sp}
    qq = {t: math.exp(Q["topk"][t]) for t in sq}
    rq = max(0.0, 1.0 - sum(qq.values()))
    miss = sp - sq
    sm = sum(pp[t] for t in miss)
    v = 0.0
    for t in sp:
        p = pp[t]
        if p <= 0:
            continue
        q = qq[t] if t in sq else (rq * pp[t] / sm if sm > 0 else rq / max(1, len(miss)))
        v += p * math.log(p / max(q, 1e-300))
    return v


def pctl(v, q):
    v = sorted(v)
    return v[min(len(v) - 1, max(0, int(round(q * (len(v) - 1)))))] if v else float("nan")


arms = {a: load(a) for a in OFF + ON}
pos = sorted(set.intersection(*[set(arms[a]) for a in OFF + ON]))
print("arms: off=%s on=%s ; 共同配对位置 n=%d" % (OFF, ON, len(pos)))


def pair(f, g):
    v, agree, top10 = [], 0, 0.0
    for p in pos:
        if arms[f][p]["tgt"] != arms[g][p]["tgt"]:
            continue
        z = kl(arms[f][p], arms[g][p])
        if z is None:
            continue
        v.append(z)
        agree += 1 if arms[f][p]["top"] == arms[g][p]["top"] else 0
        top10 += len(set(list(arms[f][p]["topk"])[:10]) & set(list(arms[g][p]["topk"])[:10])) / 10.0
    return {"n": len(v), "mean": st.mean(v), "med": st.median(v), "p90": pctl(v, .9),
            "p99": pctl(v, .99), "max": max(v), "argmax": 100.0 * agree / len(v),
            "top10": 100.0 * top10 / len(v), "gt0": 100.0 * sum(1 for x in v if x > 0) / len(v),
            "v": v}


print("\n== 逐对 ==")
off_on, on_on = [], []
for f, g in itertools.combinations(OFF + ON, 2):
    r = pair(f, g)
    kind = "off-vs-off" if (f in OFF and g in OFF) else ("on-vs-on " if (f in ON and g in ON) else "off-vs-on")
    (on_on if kind.strip() == "on-vs-on" else off_on).append(r) if kind != "off-vs-off" else None
    print("  %-10s %s||%s n=%-5d mean %.6f med %.6f p90 %.5f p99 %.5f max %.3f | argmax %5.2f%% top10 %5.1f%% | KL=0 %5.1f%%"
          % (kind, f, g, r["n"], r["mean"], r["med"], r["p90"], r["p99"], r["max"],
             r["argmax"], r["top10"], 100 - r["gt0"]))

print("\n== 把「对」当样本（每组 n=对的数量）==")
for tag, grp in (("on-vs-on", on_on), ("off-vs-on", off_on)):
    ms = [r["mean"] for r in grp]
    md = [r["med"] for r in grp]
    ar = [r["argmax"] for r in grp]
    print("  %-10s n_pairs=%d  KL均值: %.6f..%.6f (中位 %.6f)  KL中位: %.6f..%.6f  argmax: %.2f%%..%.2f%%"
          % (tag, len(grp), min(ms), max(ms), st.median(ms), min(md), max(md), min(ar), max(ar)))

if on_on and off_on:
    mu = [r["mean"] for r in on_on]
    mo = [r["mean"] for r in off_on]
    print("\n  判读：off-vs-on 的 KL 均值 %s；on-vs-on 的 %s"
          % (["%.4f" % x for x in sorted(mo)], ["%.4f" % x for x in sorted(mu)]))
    overlap = min(mo) <= max(mu) if len(mu) > 1 else None
    print("  区间是否重叠: %s（重叠 => 差异落在「同一配置两次」的浮动内）" % overlap)

print("\n== PPL（仅记录）==")
for a in OFF + ON:
    v = [x["lp_tgt"] for x in arms[a].values()]
    print("  %-2s %-4s PPL %.4f  top1 命中 %.2f%%"
          % (a, "off" if a in OFF else "on", math.exp(-st.mean(v)),
             100.0 * sum(x["is_top"] for x in arms[a].values()) / len(arms[a])))
