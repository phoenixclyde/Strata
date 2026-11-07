# -*- coding: utf-8 -*-
"""W803 KL 分析器：CPU prefill share 的质量门。

输入 /home/albus/strata166/data/w803_logpos_<arm>.tsv（8 定值列 + K 个 id:logprob）
  列：pos / tgt / logprob(tgt) / top_id / logprob(top) / is_top / logprob(extra) / logprob(tgt without extra)

口径与 W767 一致（`kl_prop`：两臂 top-K 并集 + REST 桶，缺失质量按 ref 比例铺开），
并给出 mass covered / argmax 一致率 / top-10 重叠，避免只看一个数。

四臂语义（W803）：
  A = share 0        （生产值）
  B = share auto
  C = share 0（第二次）
  D = share auto（第二次）
  => C||A = 同配置两次装载的**底噪**
     D||B = share 自己的**逐次浮动**（上游 #2685 的 RTX 4070S 报告：share 让 prefill 逐次不同）
     B||A / D||A = 「开 share」与「关 share」的差
判据：B||A 若与 max(C||A, D||B) 同量级 => 差异落在引擎自身噪声内（上游 DETAILS.md 表里 CPU_SHARE 行
      0.0006-0.0007 与「同一引擎跑两遍」的 0.0006-0.0007 同值，正是这个结构）。
"""
import io, math, os, statistics as st, sys

D = sys.argv[1] if len(sys.argv) > 1 else r"D:/workbuddy_space/strata_ws/albus/w803"
ARMS = [a.strip() for a in (sys.argv[2].split(",") if len(sys.argv) > 2 else
                            ["A", "B", "C", "D"])]
SPLIT = int(sys.argv[3]) if len(sys.argv) > 3 else -1    # pos < SPLIT 视为「注入前控制段」


def load(arm):
    p = os.path.join(D, "w803_logpos_%s.tsv" % arm)
    if not os.path.isfile(p):
        return None
    rows, nf = {}, None
    with io.open(p, encoding="utf-8") as f:
        for line in f:
            line = line.rstrip("\n")
            if not line:
                continue
            c = line.split("\t")
            nf = nf or len(c)
            pos, tgt = int(c[0]), int(c[1])
            topk = {}
            for x in c[8:]:
                if ":" not in x:
                    continue
                i, v = x.split(":", 1)
                topk[int(i)] = float(v)
            rows[pos] = {"tgt": tgt, "lp_tgt": float(c[2]), "top": int(c[3]), "lp_top": float(c[4]),
                         "is_top": int(c[5]), "lp_extra": float(c[6]), "topk": topk}
    return rows, nf


def kl_prop(P, Q):
    sp, sq = set(P["topk"]), set(Q["topk"])
    if not sp or not sq:
        return None
    pp = {t: math.exp(P["topk"][t]) for t in sp}
    qq = {t: math.exp(Q["topk"][t]) for t in sq}
    cp, cq = sum(pp.values()), sum(qq.values())
    rq = max(0.0, 1.0 - cq)
    missing = sp - sq
    sm = sum(pp[t] for t in missing)
    q = {}
    for t in sp:
        if t in sq:
            q[t] = qq[t]
        else:                      # Q's residual spread over P's tokens it does not list, proportional to P
            q[t] = rq * (pp[t] / sm) if sm > 0 else rq / max(1, len(missing))
    kl, tot = 0.0, 0.0
    for t in sp:
        p = pp[t]
        if p <= 0:
            continue
        tot += p
        kl += p * math.log(p / max(q[t], 1e-300))
    return kl, cp, cq


def pctl(v, q):
    v = sorted(v)
    if not v:
        return float("nan")
    i = min(len(v) - 1, max(0, int(round(q * (len(v) - 1)))))
    return v[i]


def compare(ref, arm, sel=None):
    R, A = ref, arm
    pos = sorted(set(R) & set(A))
    if sel is not None:
        pos = [p for p in pos if sel(p)]
    kls, agree, top10, dlp, n_pair, skip = [], 0, 0, [], 0, 0
    for p in pos:
        r, a = R[p], A[p]
        if r["tgt"] != a["tgt"]:
            skip += 1
            continue
        z = kl_prop(r, a)
        if z is None:
            skip += 1
            continue
        kls.append(z[0])
        n_pair += 1
        agree += 1 if r["top"] == a["top"] else 0
        top10 += len(set(list(r["topk"])[:10]) & set(list(a["topk"])[:10])) / 10.0
        dlp.append(a["lp_top"] - r["lp_top"])
    if not n_pair:
        return None
    return {"n": n_pair, "skip": skip, "kl_mean": st.mean(kls), "kl_med": st.median(kls),
            "kl_p90": pctl(kls, .9), "kl_p99": pctl(kls, .99), "kl_max": max(kls),
            "argmax": 100.0 * agree / n_pair, "top10": 100.0 * top10 / n_pair,
            "d_lp_top": st.mean(dlp), "gt0": 100.0 * sum(1 for x in kls if x > 0) / n_pair}


def ppl(rows):
    v = [r["lp_tgt"] for r in rows.values()]
    return math.exp(-st.mean(v)) if v else float("nan")


def line(tag, c):
    if c is None:
        print("  %-12s (no pairs)" % tag); return
    print("  %-12s n=%-5d KL mean %.6f med %.6f p90 %.5f p99 %.5f max %.4f | argmax %5.2f%% "
          "top10 %5.1f%% | d_lp(top) %+.5f | KL>0 %5.1f%%"
          % (tag, c["n"], c["kl_mean"], c["kl_med"], c["kl_p90"], c["kl_p99"], c["kl_max"],
             c["argmax"], c["top10"], c["d_lp_top"], c["gt0"]))


arms = {}
for a in ARMS:
    z = load(a)
    if z is None:
        print("ARM %s MISSING" % a); continue
    arms[a] = z[0]
    print("ARM %-2s rows=%-5d uniq_pos=%-5d fields=%d  PPL=%.4f  pos[%d..%d]"
          % (a, sum(1 for _ in open(os.path.join(D, "w803_logpos_%s.tsv" % a))), len(z[0]), z[1],
             ppl(z[0]), min(z[0]), max(z[0])))

print("\n== 全部配对位置 ==")
for pair in [("A", "C"), ("B", "D"), ("A", "B"), ("A", "D"), ("B", "C")]:
    if pair[0] in arms and pair[1] in arms:
        line("%s||%s" % pair, compare(arms[pair[0]], arms[pair[1]]))

if SPLIT > 0:
    print("\n== 注入前控制段 pos < %d（share 还没跑过，应≈0）==" % SPLIT)
    for pair in [("A", "C"), ("B", "D"), ("A", "B")]:
        if pair[0] in arms and pair[1] in arms:
            line("%s||%s" % pair, compare(arms[pair[0]], arms[pair[1]], lambda p: p < SPLIT))
    print("\n== 注入后 pos >= %d ==" % SPLIT)
    for pair in [("A", "C"), ("B", "D"), ("A", "B"), ("A", "D"), ("B", "C")]:
        if pair[0] in arms and pair[1] in arms:
            line("%s||%s" % pair, compare(arms[pair[0]], arms[pair[1]], lambda p: p >= SPLIT))
