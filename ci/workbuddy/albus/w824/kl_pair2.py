"""W824: 用 kl_prop（kl_gate.py 的口径）算配对 KL。
列格式：pos tgt lp_tgt top lp_top is_top lp_extra lp_tgt_wo_extra  + K 个 id:logprob
"""
import io, math, os, sys, statistics as st

D = sys.argv[1] if len(sys.argv) > 1 else '/home/albus/strata166/data/w824kl'
PAIRS = [('Q1', 'Q1b'), ('Q1', 'Q0'), ('Q1b', 'Q0')]   # 前一个是"参照"（P）


def load(arm):
    rows = {}
    with io.open(os.path.join(D, 'w803_logpos_%s.tsv' % arm), encoding='utf-8') as f:
        for line in f:
            line = line.rstrip('\n')
            if not line:
                continue
            c = line.split('\t')
            topk = {}
            for x in c[8:]:
                if ':' in x:
                    i, v = x.split(':', 1)
                    topk[int(i)] = float(v)
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
        if t in sq:
            q = qq[t]
        else:
            q = rq * (pp[t] / sm) if sm > 0 else rq / max(1, len(missing))
        kl += p * math.log(p / max(q, 1e-300))
    return kl


ARMS = tuple(sys.argv[2].split(',')) if len(sys.argv) > 2 else ('Q1', 'Q0', 'Q1b')
A = {a: load(a) for a in ARMS}
print('%-12s %5s %10s %10s %9s %9s %10s' % ('pair', 'n', 'KL mean', 'KL median', 'argmax同', 'top10重叠', 'mean Δlp_tgt'))
for p, q in ((ARMS[0], ARMS[2]), (ARMS[0], ARMS[1]), (ARMS[2], ARMS[1])):
    P, Q = A[p], A[q]
    pos = sorted(set(P) & set(Q))
    kls, agree, ov, dlp = [], 0, 0, []
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
    n = len(pos)
    print('%-12s %5d %10.4f %10.4f %8.1f%% %9.2f %10.4f'
          % (p + '||' + q, n, st.mean(kls) if kls else float('nan'),
             st.median(kls) if kls else float('nan'),
             100.0 * agree / n, ov / n, st.mean(dlp)))
