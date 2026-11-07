python3 - <<'PY'
import re, statistics as st
L = '/home/albus/strata166/data/strata-huihui-ud-iq4_xs.log'
pat = re.compile(r'strata decode timing: (\d+) windows, avg T ([\d.]+), ([\d.]+) tokens/window, ([\d.]+) ms/window = '
                 r'adapt wait ([\d.]+) \+ verify ([\d.]+) \(GPU-reach wait ([\d.]+) \+ per-layer host ([\d.]+)')
pat2 = re.compile(r'CPU experts ([\d.]+) \(([\d.]+) entries\), VRAM hits ([\d.]+), PCIe ([\d.]+)')

lines = open(L, encoding='utf-8', errors='replace').read().split('\n')
recs = []
for i, ln in enumerate(lines):
    m = pat.search(ln)
    if not m:
        continue
    m2 = None
    for j in range(i, min(i + 6, len(lines))):
        m2 = pat2.search(lines[j])
        if m2:
            break
    win, T, tpw, mpw = int(m.group(1)), float(m.group(2)), float(m.group(3)), float(m.group(4))
    reach = float(m.group(7))
    cpu = float(m2.group(1)) if m2 else float('nan')
    hits = float(m2.group(3)) if m2 else float('nan')
    recs.append(dict(win=win, T=T, tpw=tpw, mpw=mpw, reach=reach, cpu=cpu, hits=hits,
                     tps=1000.0 * tpw / mpw))

print('total timing lines in log:', len(recs))
tail = recs[-32:]
labels = ['ta(4/.70)', 'tf(8/.70)', 'tg(8/.50)', 'th(8/.50+cost)', 'ta2', 'tk(8/.85)', 'tl(8/.90)', 'ta3']
assert len(tail) == 32, len(tail)

print()
print('%-15s %-6s %6s %7s %8s %8s %7s %7s' % ('arm', 'req', 'win', 'T', 'tok/win', 'ms/win', 'tok/s', 'reach'))
agg = []
for k, lab in enumerate(labels):
    grp = tail[k * 4:(k + 1) * 4]
    body = [r for r in grp if r['win'] >= 100]     # drop the 16-token warm-up
    for idx, r in enumerate(grp):
        tag = 'warm' if r['win'] < 100 else 'p%d' % (idx - 1)
        print('%-15s %-6s %6d %6.2f %7.2f %8.2f %8.2f %7.2f' % (
            lab if idx == 0 else '', tag, r['win'], r['T'], r['tpw'], r['mpw'], r['tps'], r['reach']))
    med = lambda k2: st.median([r[k2] for r in body])
    agg.append((lab, med('T'), med('tpw'), med('mpw'), med('tps'), med('reach'), med('cpu'), med('hits')))
    print('%-15s %-6s %6s %6.2f %7.2f %8.2f %8.2f' % ('', 'MED', '', med('T'), med('tpw'), med('mpw'), med('tps'), ))

print()
print('%-15s %5s %8s %8s %8s %8s %7s %7s' % ('arm', 'T', 'tok/win', 'ms/win', 'tok/s', 'reach', 'cpuExp', 'vramHit'))
base = None
for lab, T, tpw, mpw, tps, reach, cpu, hits in agg:
    if lab.startswith('ta') and base is None:
        base = tps
    print('%-15s %5.2f %8.2f %8.2f %8.2f %8.2f %7.2f %7.2f   %+5.1f%%' % (
        lab, T, tpw, mpw, tps, reach, cpu, hits, 100.0 * (tps / base - 1.0)))
PY
