python3 - <<'PY'
import re, statistics
for arm in ('b154n','b154na'):
    p='/home/albus/strata166/data/w828_ab_%s.txt'%arm
    try:
        s=open(p,encoding='utf-8',errors='replace').read()
    except FileNotFoundError:
        print(arm,'missing'); continue
    # split into arm segments
    segs=re.split(r'=== ARM ', s)
    print('==',arm,'segments',len(segs)-1)
    for i,seg in enumerate(segs[1:],1):
        vals=[float(m) for m in re.findall(r'decode=\s*[\d.]+\s*ms\s+([\d.]+) tok/s', seg)]
        med=[float(m) for m in re.findall(r'MEDIAN decode_tps = ([\d.]+)', seg)]
        reads=re.findall(r'prompt_tokens=(\d+)\s+wall=([\d.]+)s', seg)
        if vals:
            print('  seg%d n=%d vals=%s median=%.2f  declared=%s' % (i,len(vals),vals,statistics.median(vals),med))
            print('        reads=%s' % (reads,))
PY
