import subprocess, base64, re, statistics

SCRIPT = r'''
L=/home/albus/strata166/data/strata-huihui-ud-iq4_xs.log
grep -a "decode GPU stages" $L
'''


def run(script):
    p = subprocess.run(['ssh', '-o', 'BatchMode=yes', 'albus@192.168.50.166', 'base64 -d | bash'],
                       input=base64.b64encode(script.encode()), stdout=subprocess.PIPE,
                       stderr=subprocess.STDOUT, timeout=240)
    return p.stdout.decode('utf-8', 'replace')


def f(pat, ln, default=None):
    m = re.search(pat + r' ([\d.]+)', ln)
    return float(m.group(1)) if m else default


rows = []
for ln in run(SCRIPT).splitlines():
    m = re.search(r'total ([\d.]+) ms/window over (\d+) windows', ln)
    if not m:
        continue
    tot, win = float(m.group(1)), int(m.group(2))
    gdn = ln.split('QSA layers:')[0]
    qsa = ln.split('QSA layers:')[1] if 'QSA layers:' in ln else ''
    if not qsa:
        continue
    d = dict(
        win=win, total=tot,
        hc_down=(f('hc0 down', gdn, 0) + f('hc1 down', gdn, 0) + f('hc0 down', qsa, 0) + f('hc1 down', qsa, 0)),
        hc_up=(f('hc0 up', gdn, 0) + f('hc1 up', gdn, 0) + f('hc0 up', qsa, 0) + f('hc1 up', qsa, 0)),
        gemv=(f(r'q8\+qkv/q-idx gemv', gdn, 0) + f('q8+kv-idx', qsa, 0) + f(r'q\+q-idx', qsa, 0)),
        router=(f(r'router\+plan\+bell', gdn, 0) + f(r'router\+plan\+bell', qsa, 0)),
        attn=(f('attention', qsa, 0) + f('scores\+topk', qsa, 0)),
        exps=(f('VRAM hits', gdn, 0) + f('waitB', gdn, 0) + f('waitCPU', gdn, 0)
              + f('VRAM hits', qsa, 0) + f('waitB', qsa, 0) + f('waitCPU', qsa, 0)),
    )
    rows.append(d)

m_rows = [r for r in rows if r['win'] >= 90]
print('M 档（>=90 窗口）样本 %d 条：' % len(m_rows))
for r in m_rows:
    print('  win=%-3d total=%-6.2f hc_down=%-5.2f hc_up=%-5.2f gemv=%-5.2f router=%-5.2f attn=%-5.2f' % (
        r['win'], r['total'], r['hc_down'], r['hc_up'], r['gemv'], r['router'], r['attn']))

print()
print('%-12s %-7s %-7s %-7s %-7s %s' % ('指标', 'min', 'median', 'max', '极差%', '相对中位'))
for k in ('total', 'hc_down', 'hc_up', 'gemv', 'router', 'attn', 'exps'):
    v = [r[k] for r in m_rows]
    mn, md, mx = min(v), statistics.median(v), max(v)
    print('%-12s %-7.2f %-7.2f %-7.2f %-7.1f ±%.1f%%' % (k, mn, md, mx, (mx - mn) / md * 100, (mx - mn) / 2 / md * 100))
