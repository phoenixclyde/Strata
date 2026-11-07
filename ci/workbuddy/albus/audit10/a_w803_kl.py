#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""AUDIT10 · W803 六臂 teacher-forced KL 的独立复算。
   支撑集用 **union**（P 有 Q 无 → 用 Q 的残差质量按 P 形状分配），与 kl_gate*.py 的写法不同但数学等价。
   同时给出：位置数、argmax 一致率、KL==0 占比、KL 均值/中位/p90/p99/max。
"""
import glob
import itertools
import math
import os
import statistics as st
import sys


def load(path):
    rows = {}
    for ln in open(path, encoding="utf-8"):
        c = ln.rstrip("\n").split("\t")
        if len(c) < 9:
            continue
        tk = {}
        for f in c[8:]:
            if ":" in f:
                i, v = f.split(":", 1)
                tk[int(i)] = float(v)
        rows[int(c[0])] = {"tgt": int(c[1]), "lptgt": float(c[2]), "top": int(c[3]), "tk": tk}
    return rows


def kl_union(A, B):
    """KL(P||Q)，两边都用**原始 exp(lp)**（不归一），未列出的部分算残差质量。
       自检：A 与 B 的 top-k 完全相同时必须恰好 0。"""
    p = {t: math.exp(v) for t, v in A["tk"].items()}
    q = {t: math.exp(v) for t, v in B["tk"].items()}
    if not p or not q:
        return None
    rq = max(0.0, 1.0 - sum(q.values()))          # Q 未列出的长尾质量
    miss = [t for t in p if t not in q]
    sm = sum(p[t] for t in miss)
    v = 0.0
    for t, pv in p.items():
        if pv <= 0:
            continue
        if t in q:
            qv = q[t]
        elif sm > 0:
            qv = rq * pv / sm
        else:
            qv = rq / max(1, len(miss))
        v += pv * math.log(pv / max(qv, 1e-300))
    return v


def stats(name, vals, argmax_same, n):
    vals = [v for v in vals if v is not None]
    if not vals:
        print("  %-14s (no data)" % name)
        return None
    s = sorted(vals)
    zero = 100.0 * sum(1 for v in vals if v == 0.0) / len(vals)
    print("  %-14s n=%-5d mean %.6f  med %.6f  p90 %.4f  p99 %.4f  max %.3f | argmax %5.2f%% | KL=0 %5.1f%%"
          % (name, len(vals), st.mean(vals), st.median(vals), s[int(0.9 * len(s)) - 1],
             s[int(0.99 * len(s)) - 1], max(vals), 100.0 * argmax_same / n, zero))
    return st.mean(vals)


def main(d="albus/w803"):
    arms = {os.path.basename(p).split("_")[-1].split(".")[0]: load(p)
            for p in sorted(glob.glob(os.path.join(d, "w803_logpos_*.tsv")))}
    print("臂：%s" % ", ".join("%s=%d 行" % (k, len(v)) for k, v in sorted(arms.items())))
    keys = sorted(arms)
    common = set.intersection(*[set(v) for v in arms.values()])
    print("公共位置 %d（各臂位置数 %s）" % (len(common), {k: len(v) for k, v in arms.items()}))
    pos = sorted(common)
    print("\n逐对：")
    res = {}
    for a, b in itertools.combinations(keys, 2):
        vals, am = [], 0
        for p in pos:
            A, B = arms[a][p], arms[b][p]
            if A["tgt"] != B["tgt"]:
                continue
            vals.append(kl_union(A, B))
            am += 1 if A["top"] == B["top"] else 0
        res[(a, b)] = stats("%s||%s" % (a, b), vals, am, len(pos))
    print("\n字节级一致性（同配置两遍应当是 0）：")
    for a, b in itertools.combinations(keys, 2):
        same = sum(1 for p in pos if arms[a][p]["tk"] == arms[b][p]["tk"])
        if same == len(pos):
            print("  %s 与 %s：top-64 逐位相同（%d/%d 位置）" % (a, b, same, len(pos)))


if __name__ == "__main__":
    main(sys.argv[1] if len(sys.argv) > 1 else "albus/w803")
