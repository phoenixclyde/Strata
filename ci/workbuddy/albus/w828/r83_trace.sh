#!/bin/bash
# W828h: offline window-policy study from STRATA_SPEC_TRACE (T a sfx ms p1..p7 per round).
python3 - <<'PY'
import os, statistics as st

TR = '/home/albus/strata166/data/w828_trace'

def load(arm):
    f = os.path.join(TR, 'spec_%s.txt' % arm)
    if not os.path.exists(f):
        return None
    out = []
    for ln in open(f, encoding='utf-8', errors='replace'):
        p = ln.split()
        if len(p) < 4:
            continue
        T, a, sfx, ms = int(p[0]), int(p[1]), int(p[2]), float(p[3])
        probs = [float(x) for x in p[4:]]
        out.append((T, a, sfx, ms, probs))
    return out

print('=== trace inventory ===')
data = {}
for arm in ['ta', 'tf', 'tg', 'th']:
    d = load(arm)
    if d is None:
        print('%-3s (no trace)' % arm); continue
    data[arm] = d
    Ts = [r[0] for r in d]
    hist = {t: Ts.count(t) for t in sorted(set(Ts))}
    print('%-3s rounds=%4d  T hist=%s  mean tok/round=%.2f  mean ms=%.1f'
          % (arm, len(d), hist, st.mean([r[1] + 1 for r in d]), st.mean([r[3] for r in d])))

# ms(T) curve per arm: linear fit plus the measured medians
print()
print('=== measured ms by width (median per T, rounds with that T) ===')
curve = {}
for arm, d in data.items():
    by = {}
    for T, a, sfx, ms, probs in d:
        by.setdefault(T, []).append(ms)
    row = {T: st.median(v) for T, v in by.items() if len(v) >= 15}
    curve[arm] = row
    print('%-3s %s' % (arm, '  '.join('T%d=%.1f(n%d)' % (T, row[T], len(by[T])) for T in sorted(row))))

# acceptance by depth (realized), from the trace: a >= d+1 means draft d accepted
print()
print('=== draft acceptance by depth (realized, only depths the window reached) ===')
for arm, d in data.items():
    line = []
    for depth in range(0, 7):
        tested = [r for r in d if r[0] > depth + 1]   # window had rows to test this draft
        if len(tested) < 15:
            break
        ok = sum(1 for r in tested if r[1] > depth)
        line.append('d%d=%.1f%%(n%d)' % (depth, 100.0 * ok / len(tested), len(tested)))
    print('%-3s %s' % (arm, '  '.join(line)))

# counterfactual policy: cap C, gate P, using the widest trace as the sample
print()
print('=== counterfactual: cap x gate, predicted from the 8-wide trace ===')
src = data.get('tg') or data.get('tf')
if not src:
    print('(need tf/tg trace)')
else:
    # ms model: median ms per achieved width, fall back to linear growth
    by = {}
    for T, a, sfx, ms, probs in src:
        by.setdefault(T, []).append(ms)
    med = {T: st.median(v) for T, v in by.items() if len(v) >= 10}
    if med:
        k = med.get(8, max(med.values()))
        base = min(med.values())
        # assume the unobserved wide widths cost at least the widest observed one
        for T in range(1, 9):
            med.setdefault(T, k if T > max(med) else base)
    print('ms model:', '  '.join('T%d=%.1f' % (T, med[T]) for T in sorted(med)))
    print()
    print('%-3s %-5s %8s %8s %9s' % ('cap', 'gate', 'tok/win', 'ms/win', 'tok/s'))
    best = None
    for cap in (2, 3, 4, 5, 6, 8):
        for gate in (0.0, 0.3, 0.5, 0.7, 0.9):
            toks, mss = [], []
            for T, a, sfx, ms, probs in src:
                if sfx:
                    continue
                R = 1
                for p in probs[:cap - 1]:
                    if p >= gate:
                        R += 1
                    else:
                        break
                acc = min(a, R - 1)
                toks.append(acc + 1)
                mss.append(med[R])
            tw, mw = st.mean(toks), st.mean(mss)
            tps = 1000.0 * tw / mw
            if best is None or tps > best[0]:
                best = (tps, cap, gate, tw, mw)
            print('%-3d %-5.2f %8.2f %8.2f %9.2f' % (cap, gate, tw, mw, tps))
    print()
    print('predicted best: cap=%d gate=%.2f -> %.2f tok/s (%.2f tok/win, %.2f ms/win)'
          % (best[1], best[2], best[0], best[3], best[4]))
PY
