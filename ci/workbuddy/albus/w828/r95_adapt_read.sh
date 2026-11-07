python3 - <<'PY'
import re, statistics as st
L = '/home/albus/strata166/data/strata-huihui-ud-iq4_xs.log'
pat = re.compile(r'strata decode timing: (\d+) windows, avg T ([\d.]+), ([\d.]+) tokens/window, ([\d.]+) ms/window = '
                 r'adapt wait ([\d.]+) \+ verify ([\d.]+) \(GPU-reach wait ([\d.]+) \+ per-layer host ([\d.]+)')
pat2 = re.compile(r'CPU experts ([\d.]+) \(([\d.]+) entries\), VRAM hits ([\d.]+), PCIe ([\d.]+)')
pat3 = re.compile(r'adapt join ([\d.]+) \+ other ([\d.]+)')
pat4 = re.compile(r'(\d+) swaps/window')

lines = open(L, encoding='utf-8', errors='replace').read().split('\n')
recs = []
for i, ln in enumerate(lines):
    m = pat.search(ln)
    if not m:
        continue
    r = dict(win=int(m.group(1)), T=float(m.group(2)), tpw=float(m.group(3)), mpw=float(m.group(4)),
             aw=float(m.group(5)), reach=float(m.group(7)))
    tail = ' '.join(lines[i:i + 6])
    m2, m3, m4 = pat2.search(tail), pat3.search(tail), pat4.search(tail)
    r['cpu'] = float(m2.group(1)) if m2 else float('nan')
    r['hits'] = float(m2.group(3)) if m2 else float('nan')
    r['join'] = float(m3.group(1)) if m3 else float('nan')
    r['other'] = float(m3.group(2)) if m3 else float('nan')
    r['swaps'] = float(m4.group(1)) if m4 else float('nan')
    r['tps'] = 1000.0 * r['tpw'] / r['mpw']
    recs.append(r)

tail = recs[-16:]
labels = ['ta', 'tm(adapt off)', 'tm2(adapt off)', 'ta2']
print('timing lines total', len(recs), 'using last 16')
print('%-16s %-5s %6s %6s %7s %8s %8s %7s %7s %6s %6s' % (
    'arm', 'req', 'win', 'T', 'tok/win', 'ms/win', 'tok/s', 'adaptW', 'swaps', 'cpuExp', 'vram'))
agg = []
for k, lab in enumerate(labels):
    grp = tail[k * 4:(k + 1) * 4]
    body = [r for r in grp if r['win'] >= 100]
    for idx, r in enumerate(grp):
        tag = 'warm' if r['win'] < 100 else 'p%d' % (idx - 1)
        print('%-16s %-5s %6d %6.2f %7.2f %8.2f %8.2f %7.2f %7.1f %6.2f %6.2f' % (
            lab if idx == 0 else '', tag, r['win'], r['T'], r['tpw'], r['mpw'], r['tps'],
            r['aw'], r['swaps'], r['cpu'], r['hits']))
    med = lambda k2: st.median([r[k2] for r in body])
    agg.append((lab, med('T'), med('tpw'), med('mpw'), med('tps'), med('aw'), med('swaps'), med('cpu')))
    print('%-16s %-5s %6s %6.2f %7.2f %8.2f %8.2f' % ('', 'MED', '', med('T'), med('tpw'), med('mpw'), med('tps'), ))

print()
base = agg[0][4]
print('%-16s %6s %8s %8s %7s %6s %7s' % ('arm', 'T', 'tok/win', 'ms/win', 'tok/s', 'adaptW', 'swaps'))
for lab, T, tpw, mpw, tps, aw, sw, cpu in agg:
    print('%-16s %6.2f %8.2f %8.2f %7.2f %6.2f %7.1f   %+5.1f%%' % (lab, T, tpw, mpw, tps, aw, sw, 100.0 * (tps / base - 1.0)))
PY
