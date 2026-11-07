import subprocess, base64, re, statistics


def pull(glob='/home/albus/strata166/data/r0b_gov_*.txt'):
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
        gemv=num(r'q8\+qkv/q-idx gemv', gdn) + num('q8+kv-idx', qsa) + num(r'q\+q-idx', qsa),
    )


txt = pull()
print(txt.split('\n', 1)[0])
arms, cur = [], None
for ln in txt.splitlines():
    m = re.search(r'--- ARM (\d+) gov=(\w+) ', ln)
    if m:
        cur = {'n': int(m.group(1)), 'gov': m.group(2), 'rows': []}
        arms.append(cur)
        continue
    if ln.startswith('--- DISCARD') or ln.startswith('ARMS_DONE') or ln.startswith('=== '):
        cur = None
    r = parse_stage(ln)
    if r and cur and r['win'] >= 60:
        cur['rows'].append(r)

print()
print('%-4s %-12s %-6s %-7s %-8s %-8s %-8s' % ('#', 'gov', 'win', 'total', 'hc_down', 'hc_up', 'gemv'))
perf, sched = [], []
for a in arms:
    for r in a['rows']:
        print('%-4d %-12s %-6d %-7.2f %-8.2f %-8.2f %-8.2f' % (
            a['n'], a['gov'], r['win'], r['total'], r['hc_down'], r['hc_up'], r['gemv']))
        (perf if a['gov'] == 'performance' else sched).append(r)


def stat(v, key):
    x = [r[key] for r in v]
    return statistics.median(x) if x else float('nan')


print()
print('=== 交错 A/B（同进程，仅 governor 不同）===')
for key in ('total', 'hc_down', 'hc_up', 'gemv'):
    p_, s_ = stat(perf, key), stat(sched, key)
    d = (s_ - p_) / p_ * 100 if p_ == p_ and p_ else float('nan')
    print('%-8s performance %-7.2f  schedutil %-7.2f  Δ(sched-perf) %+.1f%%' % (key, p_, s_, d))
print()
print('样本数: performance=%d  schedutil=%d' % (len(perf), len(sched)))
