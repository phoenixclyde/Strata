#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""W828g: pairwise KL over three STRATA_LOGPOS dumps (kl_prop 口径, same as kl_pair2.py).
usage: kl_cmp3.py <dir> <A> <B> <C>   ->  A||B (noise floor), A||C (the effect), B||C"""
import io
import math
import os
import statistics as st
import sys

D = sys.argv[1]
NAMES = sys.argv[2:5]


def load(name):
    rows = {}
    with io.open(os.path.join(D, '%s.tsv' % name), encoding='utf-8') as f:
        for line in f:
            line = line.rstrip('\n')
            if not line:
                continue
            c = line.split('\t')
            if len(c) < 9:
                continue
            topk = {}
            for x in c[8:]:
                if ':' in x:
                    i, v = x.split(':', 1)
                    try:
                        topk[int(i)] = float(v)
                    except ValueError:
                        pass
            rows[int(c[0])] = {'tgt': int(c[1]), 'lp_tgt': float(c[2]), 'top': int(c[3]), 'topk': topk}
    return rows


def kl_prop(P, Q):
    sp, sq = set(P['topk']), set(Q['topk'])
    if not sp or not sq:
        return None
    pp = {t: math.exp(P['topk'][t]) for t in sp}
    qq = {t: math.exp(Q['topk'][t]) for t in sq}
    rq = max(0.0, 1.0 - sum(qq.values()))
    missing = sp - sq
    sm = sum(pp[t] for t in missing)
    kl = 0.0
    for t in sp:
        p = pp[t]
        if p <= 0:
            continue
        q = qq[t] if t in sq else (rq * (pp[t] / sm) if sm > 0 else rq / max(1, len(missing)))
        kl += p * math.log(p / max(q, 1e-300))
    return kl


A = {n: load(n) for n in NAMES}
print('%-16s %6s %10s %10s %9s %9s %11s' % ('pair', 'n', 'KL mean', 'KL median', 'argmax', 'top10', 'mean|dlp|'))
pairs = [(NAMES[0], NAMES[1], 'noise floor'), (NAMES[0], NAMES[2], 'EFFECT'), (NAMES[1], NAMES[2], 'effect(2nd)')]
for p, q, label in pairs:
    P, Q = A[p], A[q]
    pos = sorted(set(P) & set(Q))
    kls, agree, ov, dlp = [], 0, 0.0, []
    for i in pos:
        k = kl_prop(P[i], Q[i])
        if k is not None and k == k:
            kls.append(k)
        if P[i]['top'] == Q[i]['top']:
            agree += 1
        s1 = set(sorted(P[i]['topk'], key=P[i]['topk'].get, reverse=True)[:10])
        s2 = set(sorted(Q[i]['topk'], key=Q[i]['topk'].get, reverse=True)[:10])
        ov += len(s1 & s2) / 10.0
        dlp.append(abs(P[i]['lp_tgt'] - Q[i]['lp_tgt']))
    n = max(1, len(pos))
    print('%-16s %6d %10.4f %10.4f %8.1f%% %9.2f %11.5f   %s'
          % (p + '||' + q, len(pos),
             st.mean(kls) if kls else float('nan'),
             st.median(kls) if kls else float('nan'),
             100.0 * agree / n, ov / n,
             st.mean(dlp) if dlp else float('nan'), label))
print()
print('read: KL mean over positions (kl_prop); the noise floor must be 0.0000 for any of this to count.')
