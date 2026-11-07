#!/bin/bash
# W828h: tally the spec-window arms from the decode-timing ruler.
python3 - <<'PY'
import re, os, glob, statistics as st

DATA = '/home/albus/strata166/data'
pat = re.compile(
    r'strata decode timing: (\d+) windows, avg T ([\d.]+), ([\d.]+) tokens/window, ([\d.]+) ms/window = '
    r'adapt wait ([\d.]+) \+ verify ([\d.]+) \(GPU-reach wait ([\d.]+) \+ per-layer host ([\d.]+)')
pat2 = re.compile(r'CPU experts ([\d.]+) \(([\d.]+) entries\), VRAM hits ([\d.]+), PCIe ([\d.]+)')

print('%-4s %3s %5s %6s %8s %8s %7s %7s %7s %7s' % (
    'arm', 'T', 'win', 'tok/win', 'ms/win', 'tok/s', 'reach', 'cpuExp', 'vramHit', 'hit%'))
rows = {}
for arm in ['ta', 'tf', 'tg', 'th']:
    f = os.path.join(DATA, 'w828_ab2_%s.txt' % arm)
    if not os.path.exists(f):
        print('%-4s (no data yet)' % arm); continue
    txt = open(f, encoding='utf-8', errors='replace').read()
    a = pat.findall(txt)
    b = pat2.findall(txt)
    if not a:
        print('%-4s (no timing line)' % arm); continue
    recs = []
    for i, m in enumerate(a):
        win, T, tpw, mpw = int(m[0]), float(m[1]), float(m[2]), float(m[3])
        reach = float(m[6])
        cpu = float(b[i][0]) if i < len(b) else 0.0
        ent = float(b[i][1]) if i < len(b) else 0.0
        hit = float(b[i][2]) if i < len(b) else 0.0
        tps = 1000.0 * tpw / mpw
        recs.append((T, win, tpw, mpw, tps, reach, cpu, ent, hit))
    med = lambda xs: st.median(xs)
    row = [med([r[k] for r in recs]) for k in range(9)]
    rows[arm] = (row, recs)
    print('%-4s %3.2f %5d %6.2f %8.2f %8.2f %7.2f %7.2f %7.2f %7.1f' % (
        arm, row[0], row[1], row[2], row[3], row[4], row[5], row[6], row[7], row[8]))

if 'ta' in rows and len(rows) > 1:
    base = rows['ta'][0][4]
    print()
    print('relative to ta (by tokens/ms, the honest product):')
    for arm, (row, recs) in rows.items():
        print('  %-4s %+6.2f%%   runs: %s' % (
            arm, 100.0 * (row[4] / base - 1.0), ['%.2f' % r[4] for r in recs]))
PY
echo "--- per-arm raw (each request) ---"
for a in ta tf tg th; do
  echo "[$a]"
  grep -aE "strata decode timing" /home/albus/strata166/data/w828_ab2_$a.txt 2>/dev/null | \
    sed -E 's/strata decode timing: ([0-9]+) windows, avg T ([0-9.]+), ([0-9.]+) tokens\/window, ([0-9.]+) ms\/window.*/\1 win  T=\2  tok\/win=\3  ms\/win=\4/' | tail -4
done
