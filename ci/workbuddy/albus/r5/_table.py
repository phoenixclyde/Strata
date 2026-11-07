import subprocess, base64
def sh(s, t=120):
    p = subprocess.run(["ssh","-o","BatchMode=yes","-o","ConnectTimeout=10","albus@192.168.50.166","base64 -d | bash"],
                       input=base64.b64encode(s.encode()), stdout=subprocess.PIPE, stderr=subprocess.STDOUT, timeout=t)
    return p.stdout.decode("utf-8","replace")
print(sh(r'''
echo "=== prod ==="
curl -s --max-time 5 http://127.0.0.1:8090/health | head -c 120; echo
curl -s --max-time 5 http://127.0.0.1:8090/metrics | python3 -c "import sys,json;e=json.load(sys.stdin)['engine'];print('slots',e['expert_slots'],'vram',e['vram_free_mib'],'ver',e['version'])" 2>&1
echo "=== table ==="
python3 - <<'PY'
import re,collections
rows=[]
for ln in open('/home/albus/strata166/data/gfx906-rocblas-5.5.0.txt'):
    ln=ln.strip()
    if not ln or ln.startswith('#'): 
        if ln.startswith('STRATA_ROCBLAS'): print(ln)
        continue
    f=ln.split()
    # f16o N K ldy T sol   # default -> best
    m=re.search(r'#\s*([\d.]+) ms -> ([\d.]+) ms', ln)
    rows.append((int(f[1]),int(f[2]),int(f[4]),f[5],float(m.group(1)),float(m.group(2))))
by=collections.defaultdict(dict)
for n,k,t,sol,d,b in rows: by[(n,k)][t]=(sol,d,b)
print("%-14s %6s %8s %8s %6s"%("N x K","T","default","best","gain"))
tot=collections.defaultdict(float)
for nk,ts in sorted(by.items(), key=lambda x:-len(x[1])):
    for t in sorted(ts):
        sol,d,b=ts[t]
        print("%-14s %6d %8.3f %8.3f %6.2f %s"%("%dx%d"%nk,t,d,b,(d/b if b else 0), sol))
PY
'''))
