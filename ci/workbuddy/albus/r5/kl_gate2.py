# -*- coding: utf-8 -*-
"""W803 分析 v2：逐轮 KL + 两样本分布检验 + 首 token KL（口径与上游 DETAILS.md 对齐）。

关键结构：A 与 C 是同一个配置（share=0）跑两遍，md5 完全相同 => 底噪**恰好 0**。
于是「开 share」只有一份 off 参照、两份 on 样本 B/D：
  d_off_on = {KL(A||B)} ∪ {KL(A||D)}   （off 对 on，两次独立抽样）
  d_on_on  = {KL(B||D)}                （on 对自己，同配置两遍）
若 share 只是把切分按计时重掷（上游 #2685 的 RTX 4070S 观察），三组应同分布；
若有系统性偏置，d_off_on 会整体大于 d_on_on。
"""
import io, json, math, os, statistics as st, sys

D = sys.argv[1] if len(sys.argv) > 1 else r"D:/workbuddy_space/strata_ws/albus/w803"


def load(arm):
    rows = {}
    with io.open(os.path.join(D, "w803_logpos_%s.tsv" % arm), encoding="utf-8") as f:
        for line in f:
            c = line.rstrip("\n").split("\t")
            if len(c) < 9:
                continue
            pos, tgt = int(c[0]), int(c[1])
            topk = {}
            for x in c[8:]:
                if ":" in x:
                    i, v = x.split(":", 1)
                    topk[int(i)] = float(v)
            rows[pos] = {"tgt": tgt, "lp_tgt": float(c[2]), "top": int(c[3]), "lp_top": float(c[4]),
                         "is_top": int(c[5]), "lp_extra": float(c[6]), "topk": topk}
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
    klv = 0.0
    for t in sp:
        p = pp[t]
        if p <= 0:
            continue
        q = qq[t] if t in sq else (rq * pp[t] / sm if sm > 0 else rq / max(1, len(miss)))
        klv += p * math.log(p / max(q, 1e-300))
    return klv


def pctl(v, q):
    v = sorted(v)
    return v[min(len(v) - 1, max(0, int(round(q * (len(v) - 1)))))] if v else float("nan")


def ksd(x, y):
    """两样本 KS 统计量（足够看「是否同分布」）"""
    x, y = sorted(x), sorted(y)
    i = j = 0
    d = 0.0
    while i < len(x) and j < len(y):
        if x[i] <= y[j]:
            i += 1
        else:
            j += 1
        d = max(d, abs(i / len(x) - j / len(y)))
    return d


A, B, C, Dm = load("A"), load("B"), load("C"), load("D")
pos = sorted(set(A) & set(B))
client = json.load(open(os.path.join(D, "w803_kl_A.json"), encoding="utf-8"))["results"]
pts = [r["prompt_tokens"] for r in client]

print("== 每轮（轮 k 的评分区间 = [prompt_tokens(k-1), prompt_tokens(k))）==")
print("  轮  类型    区间         n   KL(A||B)均值 中位   KL(B||D)均值 中位   KL(A||D)均值   注入次数")
inj = 0
rows_out = []
for k, r in enumerate(client):
    lo = pts[k - 1] if k else 0
    hi = pts[k]
    ps = [p for p in pos if lo <= p < hi]
    if not ps:
        if r["kind"] != "shape0" and (k % 2) == 0:
            inj += 1
        continue
    ab = [kl(A[p], B[p]) for p in ps if A[p]["tgt"] == B[p]["tgt"]]
    bd = [kl(B[p], Dm[p]) for p in ps if B[p]["tgt"] == Dm[p]["tgt"]]
    ad = [kl(A[p], Dm[p]) for p in ps if A[p]["tgt"] == Dm[p]["tgt"]]
    ab = [x for x in ab if x is not None]
    bd = [x for x in bd if x is not None]
    ad = [x for x in ad if x is not None]
    print("  t%-2d %-7s %4d-%-4d %4d   %10.6f %8.5f   %10.6f %8.5f   %10.6f      %d"
          % (k, r["kind"], lo, hi, len(ps), st.mean(ab), st.median(ab), st.mean(bd),
             st.median(bd), st.mean(ad), inj))
    rows_out.append((k, r["kind"], len(ps), st.mean(ab), st.median(ab), st.mean(bd),
                     st.median(bd), st.mean(ad), inj))
    if r["kind"] == "shape" or (r["kind"] == "shape0"):
        inj += 1

# 首 token（每次窗口读的第一个被评分位置）
print("\n== 每次窗口读的第一个 token（上游 DETAILS.md 的 'first token' 口径）==")
first = []
for k, r in enumerate(client):
    lo = pts[k - 1] if k else 0
    hi = pts[k]
    ps = [p for p in pos if lo <= p < hi]
    if not ps:
        continue
    p = min(ps)
    if A[p]["tgt"] != B[p]["tgt"]:
        continue
    z1, z2, z3 = kl(A[p], B[p]), kl(B[p], Dm[p]), kl(A[p], Dm[p])
    first.append((p, z1, z2, z3))
    print("  pos %-5d KL(A||B) %.6f   KL(B||D) %.6f   KL(A||D) %.6f" % (p, z1, z2, z3))
print("  mean: A||B %.6f   B||D %.6f   A||D %.6f"
      % (st.mean([x[1] for x in first]), st.mean([x[2] for x in first]), st.mean([x[3] for x in first])))


def collect(f, g):
    v = []
    for p in pos:
        if f[p]["tgt"] != g[p]["tgt"]:
            continue
        z = kl(f[p], g[p])
        if z is not None:
            v.append(z)
    return v


d_off_on = collect(A, B) + collect(A, Dm)
d_on_on = collect(B, Dm)
print("\n== 同分布检验（逐位置 KL 的两个样本）==")
for tag, v in (("off-vs-on (A||B + A||D)", d_off_on), ("on-vs-on  (B||D)", d_on_on)):
    print("  %-26s n=%-5d mean %.6f med %.6f p90 %.5f p99 %.5f  KL=0 占 %.1f%%"
          % (tag, len(v), st.mean(v), st.median(v), pctl(v, .9), pctl(v, .99),
             100.0 * sum(1 for x in v if x == 0) / len(v)))
print("  KS(off-vs-on, on-vs-on) = %.4f   （同分布时不应显著）" % ksd(d_off_on, d_on_on))
print("  中位差 %.2f%%   均值差 %+.2f%%"
      % (100.0 * (st.median(d_off_on) - st.median(d_on_on)) / max(st.median(d_on_on), 1e-12),
         100.0 * (st.mean(d_off_on) - st.mean(d_on_on)) / max(st.mean(d_on_on), 1e-12)))

# PPL 与 argmax
print("\n== 标量（不作判据，仅记录：W767 已证 PPL 是偏置量）==")
for nm, r in (("A(off)", A), ("B(on)", B), ("C(off)", C), ("D(on)", Dm)):
    v = [x["lp_tgt"] for x in r.values()]
    print("  %-7s PPL %.4f  自身 top1 命中 %.2f%%  mean logprob(tgt) %.4f"
          % (nm, math.exp(-st.mean(v)), 100.0 * sum(x["is_top"] for x in r.values()) / len(r),
             st.mean(v)))
