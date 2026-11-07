import subprocess, base64, re, statistics, sys


def pull(glob):
    script = "F=$(ls -t %s | head -1); echo \"FILE=$F\"; cat \"$F\"" % glob
    p = subprocess.run(['ssh', '-o', 'BatchMode=yes', 'albus@192.168.50.166', 'base64 -d | bash'],
                       input=base64.b64encode(script.encode()), stdout=subprocess.PIPE,
                       stderr=subprocess.STDOUT, timeout=200)
    return p.stdout.decode('utf-8', 'replace')


def num(pat, s, d=0.0):
    m = re.search(pat + r' ([\d.]+)', s)
    return float(m.group(1)) if m else d


def parse_stage(ln):
    if 'decode GPU stages' not in ln:
        return None
    m = re.search(r'total ([\d.]+) ms/window over (\d+) windows', ln)
    if not m:
        return None
    gdn, _, qsa = ln.partition('QSA layers:')
    if not qsa:
        return None
    return dict(
        win=int(m.group(2)), total=float(m.group(1)),
        hc_down=num('hc0 down', gdn) + num('hc1 down', gdn) + num('hc0 down', qsa) + num('hc1 down', qsa),
        hc_up=num('hc0 up', gdn) + num('hc1 up', gdn) + num('hc0 up', qsa) + num('hc1 up', qsa),
        hc_norm=num('hc0 norm', gdn) + num('hc1 norm', gdn) + num('hc0 norm', qsa) + num('hc1 norm', qsa),
        gemv=num(r'q8\+qkv/q-idx gemv', gdn) + num('q8+kv-idx', qsa) + num(r'q\+q-idx', qsa),
    )


glob = sys.argv[1] if len(sys.argv) > 1 else '/home/albus/strata166/data/arm_*_*.txt'
txt = pull(glob)
print(txt.split('\n', 1)[0])
for ln in txt.splitlines():
    if ln.startswith(('ARM=', 'env_now', 'slots', 'governor', 'overrides')):
        print(' ', ln)

sec, rows = None, {}
for ln in txt.splitlines():
    m = re.search(r'--- (DISCARD \w+|RUN \d) ', ln)
    if m:
        sec = m.group(1)
        rows.setdefault(sec, [])
        continue
    r = parse_stage(ln)
    if r and sec and r['win'] >= 60:
        rows[sec].append(r)

print()
print('%-10s %-5s %-7s %-8s %-8s %-8s %-8s' % ('sec', 'win', 'total', 'hc_down', 'hc_up', 'gemv', 'hc_norm'))
for k, v in rows.items():
    for r in v:
        print('%-10s %-5d %-7.2f %-8.2f %-8.2f %-8.2f %-8.2f' % (
            k, r['win'], r['total'], r['hc_down'], r['hc_up'], r['gemv'], r['hc_norm']))

meas = [r for k, v in rows.items() if k.startswith('RUN') for r in v]
if meas:
    print()
    print('=== 测量臂中位（RUN 1-3）===')
    for key in ('total', 'hc_down', 'hc_up', 'hc_norm', 'gemv'):
        print('  %-8s %.2f' % (key, statistics.median([r[key] for r in meas])))
