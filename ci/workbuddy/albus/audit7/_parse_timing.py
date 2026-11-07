import subprocess, base64, re

SCRIPT = r'''
L=/home/albus/strata166/data/strata-huihui-ud-iq4_xs.log
grep -a "decode timing" $L
'''


def run(script):
    p = subprocess.run(['ssh', '-o', 'BatchMode=yes', 'albus@192.168.50.166', 'base64 -d | bash'],
                       input=base64.b64encode(script.encode()), stdout=subprocess.PIPE,
                       stderr=subprocess.STDOUT, timeout=240)
    return p.stdout.decode('utf-8', 'replace')


raw = run(SCRIPT)
pat = re.compile(
    r'(\d+) windows?, avg T ([\d.]+), ([\d.]+) tokens/window, ([\d.]+) ms/window '
    r'= verify ([\d.]+) \(GPU-reach wait ([\d.]+) \+ per-layer host ([\d.]+) \[[^\]]*\] \+ stage ([\d.]+)\) '
    r'\+ commit/emit ([\d.]+) \+ draft ([\d.]+); per layer-window: CPU experts ([\d.]+) \(([\d.]+) entries\), '
    r'VRAM hits ([\d.]+), PCIe ([\d.]+); adapt wait ([\d.]+) join ([\d.]+)')

rows = []
for ln in raw.splitlines():
    m = pat.search(ln)
    if not m:
        continue
    g = m.groups()
    rows.append(dict(n=int(g[0]), T=float(g[1]), tpw=float(g[2]), total=float(g[3]),
                     verify=float(g[4]), gpuwait=float(g[5]), host=float(g[6]), stage=float(g[7]),
                     commit=float(g[8]), draft=float(g[9]), cpu=float(g[10]), vram=float(g[12]),
                     pcie=float(g[13]), adapt=float(g[14]), join=float(g[15])))

print('parsed %d lines' % len(rows))
print()
print('%-4s %-5s %-6s %-7s %-9s %-9s %-9s %-9s' % ('n', 'T', 'tok/w', 'total', 'v+c+d', 'verifysub', 'adapt+join', 'residual'))
for r in rows:
    vcd = r['verify'] + r['commit'] + r['draft']
    sub = r['gpuwait'] + r['host'] + r['stage']
    aj = r['adapt'] + r['join']
    resid = r['total'] - (vcd + aj)
    print('%-4d %-5.2f %-6.2f %-7.2f %-9.2f %-9.2f %-9.2f %+.2f' % (
        r['n'], r['T'], r['tpw'], r['total'], vcd, sub, aj, resid))
