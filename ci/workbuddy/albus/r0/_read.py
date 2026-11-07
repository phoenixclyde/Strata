import subprocess, base64, re, statistics, sys


def pull(remote_glob='/home/albus/strata166/data/r0_results_*.txt'):
    script = "F=$(ls -t %s | head -1); echo \"FILE=$F\"; cat \"$F\"" % remote_glob
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
        router=num(r'router\+plan\+bell', gdn) + num(r'router\+plan\+bell', qsa),
        attn=num('attention', qsa) + num(r'scores\+topk', qsa),
        exps=(num('VRAM hits', gdn) + num('waitB', gdn) + num('waitCPU', gdn)
              + num('VRAM hits', qsa) + num('waitB', qsa) + num('waitCPU', qsa)),
    )


txt = pull()
head = txt.split('\n', 1)[0]
print(head)
tier = None
rows = {}
meta = []
for ln in txt.splitlines():
    m = re.search(r'--- TIER (\w) ', ln)
    if m:
        tier = m.group(1)
        rows.setdefault(tier, [])
        continue
    if ln.startswith('governor') or ln.startswith('env_injected') or ln.startswith('slots') or 'prod ready' in ln or ln.startswith('ALL_TIERS'):
        meta.append(ln.strip())
    r = parse_stage(ln)
    if r and tier and r['win'] >= (8 if tier == 'L' else 60):
        rows[tier].append(r)

for k in meta:
    print(k)

print()
print('%-4s %-5s %-7s %-8s %-8s %-8s %-8s %-8s %s' % ('tier', 'win', 'total', 'hc_down', 'hc_up', 'gemv', 'router', 'attn', 'experts'))
for t in ('M', 'S', 'L'):
    for r in rows.get(t, []):
        print('%-4s %-5d %-7.2f %-8.2f %-8.2f %-8.2f %-8.2f %-8.2f %.2f' % (
            t, r['win'], r['total'], r['hc_down'], r['hc_up'], r['gemv'], r['router'], r['attn'], r['exps']))

print()
print('=== 与 performance 时代对照（P91：M 46.13/46.44/46.90/46.26，中位 46.35）===')
for t in ('M', 'S', 'L'):
    v = rows.get(t, [])
    if not v:
        continue
    tot = [r['total'] for r in v]
    hd = [r['hc_down'] for r in v]
    hu = [r['hc_up'] for r in v]
    print('%s: n=%d  total %s  中位 %.2f | hc_down 中位 %.2f | hc_up 中位 %.2f' % (
        t, len(v), ['%.2f' % x for x in tot], statistics.median(tot),
        statistics.median(hd), statistics.median(hu)))
