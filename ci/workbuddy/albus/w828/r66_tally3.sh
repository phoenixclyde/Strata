date +%H:%M:%S
python3 - <<'PY'
import re, statistics, os
for arm in ('ta','td'):
    p='/home/albus/strata166/data/w828_%s.log'%arm
    if not os.path.exists(p): print(arm,'no log'); continue
    rows=[]
    for l in open(p,encoding='utf-8',errors='replace'):
        if 'strata decode timing' not in l: continue
        m=re.search(r'([0-9.]+) tokens/window, ([0-9.]+) ms/window', l)
        g=re.search(r'GPU-reach wait ([0-9.]+)', l)
        if m: rows.append((float(m.group(1)), float(m.group(2)), float(g.group(1)) if g else -1))
    print('==',arm,'n=%d'%len(rows))
    for r in rows: print('   %.2f tk/win  %.2f ms/win  reach %.2f' % r)
    # drop the warm-up (first row of each arm = 8 rows per arm pair; keep rows with ms<50)
    meas=[r for r in rows if r[1] < 50]
    if meas:
        print('   -> median ms/win %.2f (n=%d)  median reach %.2f' % (
              statistics.median([r[1] for r in meas]), len(meas), statistics.median([r[2] for r in meas])))
PY
