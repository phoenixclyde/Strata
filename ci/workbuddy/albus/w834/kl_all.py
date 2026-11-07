#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""W834b：把 0.0293 的五项拆开 —— 每个臂都只关一项，各自对基线 E0 算 kl_prop。"""
import io, math, os, statistics as st, sys

D = sys.argv[1] if len(sys.argv) > 1 else "D:/workbuddy_space/strata_ws/albus/w834/kl"
BASE = "E0"
ARMS = [("RT0", "STRATA_ROUTE_TAIL_SKIP=0"), ("KVFP16", "--kv fp16"),
        ("PF0", "STRATA_HIP_PROMPT_F16=0"), ("SIMT0", "STRATA_SELECT_SIMT=0"),
        ("HCQ0", "STRATA_HC_Q8=0")]


def load(name):
    rows = {}
    with io.open(os.path.join(D, "%s.tsv" % name), encoding="utf-8") as f:
        for line in f:
            line = line.rstrip("\n")
            if not line:
                continue
            c = line.split("\t")
            if len(c) < 9:
                continue
            topk = {}
            for x in c[8:]:
                if ":" in x:
                    i, v = x.split(":", 1)
                    try:
                        topk[int(i)] = float(v)
                    except ValueError:
                        pass
            rows[int(c[0])] = {"tgt": int(c[1]), "lp": float(c[2]), "top": int(c[3]), "topk": topk}
    return rows


def kl_prop(P, Q):
    sp, sq = set(P["topk"]), set(Q["topk"])
    if not sp or not sq:
        return None
    pp = {t: math.exp(P["topk"][t]) for t in sp}
    qq = {t: math.exp(Q["topk"][t]) for t in sq}
    rq = max(0.0, 1.0 - sum(qq.values()))
    miss = sp - sq
    sm = sum(pp[t] for t in miss)
    kl = 0.0
    for t in sp:
        p = pp[t]
        if p <= 0:
            continue
        q = qq[t] if t in sq else (rq * (pp[t] / sm) if sm > 0 else rq / max(1, len(miss)))
        kl += p * math.log(p / max(q, 1e-300))
    return kl


A = load(BASE)
print("%-24s %4s %10s %10s %8s %7s %11s" % ("关掉的项", "n", "KL mean", "KL median", "argmax", "top10", "mean|dlp|"))
tot = 0.0
for name, label in ARMS:
    B = load(name)
    pos = sorted(set(A) & set(B))
    kls, agree, ov, dlp = [], 0, [], []
    for i in pos:
        k = kl_prop(A[i], B[i])
        if k is not None and k == k:
            kls.append(k)
        if A[i]["top"] == B[i]["top"]:
            agree += 1
        s1 = set(sorted(A[i]["topk"], key=A[i]["topk"].get, reverse=True)[:10])
        s2 = set(sorted(B[i]["topk"], key=B[i]["topk"].get, reverse=True)[:10])
        ov.append(len(s1 & s2) / 10.0)
        dlp.append(abs(A[i]["lp"] - B[i]["lp"]))
    m = st.mean(kls) if kls else float("nan")
    tot += m
    print("%-24s %4d %10.4f %10.4f %7.1f%% %7.2f %11.5f"
          % (label, len(pos), m, st.median(kls) if kls else float("nan"),
             100.0 * agree / max(1, len(pos)), st.mean(ov), st.mean(dlp)))
print("\n五项逐项之和 = %.4f（注意：KL 不可严格相加，这只是量级参考）" % tot)
