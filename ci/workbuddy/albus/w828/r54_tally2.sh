date +%H:%M:%S
python3 - <<'PY'
import re, statistics, os
for arm in ('ta','tc'):
    p='/home/albus/strata166/data/w828_%s.log'%arm
    if not os.path.exists(p):
        print('==',arm,'(no log)'); continue
    lines=[l for l in open(p,encoding='utf-8',errors='replace') if 'strata decode timing' in l]
    tail=lines[-4:]
    print('==',arm,'total timing lines',len(lines),'| last 4:')
    ms=[]; gr=[]; tok=[]
    for l in tail:
        m=re.search(r'([0-9.]+) tokens/window, ([0-9.]+) ms/window', l)
        g=re.search(r'GPU-reach wait ([0-9.]+)', l)
        t=re.search(r'per layer-window: CPU experts', l)
        print('   %8s tk/win %8s ms/win   GPU-reach %8s' % (m.group(1) if m else '?', m.group(2) if m else '?', g.group(1) if g else '?'))
        if m: ms.append(float(m.group(2))); tok.append(float(m.group(1)))
        if g: gr.append(float(g.group(1)))
    if ms:
        print('   -> median ms/win %.2f  (n=%d)  |  median GPU-reach %.2f  |  median tokens/win %.2f'
              % (statistics.median(ms), len(ms), statistics.median(gr) if gr else -1, statistics.median(tok)))
PY
echo "--- running ---"
docker ps --format '{{.Names}} {{.Status}}' | grep w828 || echo none
