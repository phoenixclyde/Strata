import subprocess, base64, re

SCRIPT = r'''
F=$(ls -t /home/albus/strata166/data/r0_results_*.txt | head -1)
grep -a "decode GPU stages" "$F" | grep -a " 97 windows"
'''


def run(script):
    p = subprocess.run(['ssh', '-o', 'BatchMode=yes', 'albus@192.168.50.166', 'base64 -d | bash'],
                       input=base64.b64encode(script.encode()), stdout=subprocess.PIPE,
                       stderr=subprocess.STDOUT, timeout=120)
    return p.stdout.decode('utf-8', 'replace')


txt = run(SCRIPT).strip()
if not txt:
    print('NO LINE')
    raise SystemExit

ln = txt.splitlines()[-1]
gdn, _, qsa = ln.partition('QSA layers:')

# 逐个 token 抓 "名字 数字" 对
pat = re.compile(r'([A-Za-z0-9_+\-/().]+(?: [A-Za-z0-9_+\-/().]+)*?) (\d+\.\d+)')


def harvest(seg, tag):
    out = []
    for m in re.finditer(r'([a-z0-9_+\-][a-z0-9 _+\-/().]*?) (\d+\.\d+)', seg):
        name, val = m.group(1).strip(), float(m.group(2))
        if len(name) > 34:
            name = name[-34:]
        out.append((tag + ' ' + name, val))
    return out


items = harvest(gdn, 'GDN') + harvest(qsa, 'QSA')
seen = {}
for n, v in items:
    seen[n] = seen.get(n, 0.0) + v

tot = float(re.search(r'total ([\d.]+) ms/window', ln).group(1))
print('total = %.2f ms/window' % tot)
print()
for n, v in sorted(seen.items(), key=lambda kv: -kv[1])[:30]:
    print('%-40s %6.2f  %5.1f%%' % (n, v, v / tot * 100))
