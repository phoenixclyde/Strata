import subprocess, base64, re, collections, io
def sh(s, t=120):
    p = subprocess.run(["ssh","-o","BatchMode=yes","-o","ConnectTimeout=10","albus@192.168.50.166","base64 -d | bash"],
                       input=base64.b64encode(s.encode()), stdout=subprocess.PIPE, stderr=subprocess.STDOUT, timeout=t)
    return p.stdout.decode("utf-8","replace")
raw = sh("cat /home/albus/strata166/data/gfx906-rocblas-5.5.0.txt")
io.open(r"D:/workbuddy_space/strata_ws/albus/r5/gfx906-rocblas-5.5.0.txt","w",encoding="utf-8",newline="\n").write(raw)
rows=[]
for ln in raw.splitlines():
    if not ln.startswith("f16o "): continue
    f=ln.split()
    m=re.search(r'#\s*([\d.]+) ms(?: -> ([\d.]+) ms)?', ln)
    d=float(m.group(1)); b=float(m.group(2)) if m.group(2) else d
    rows.append((int(f[1]),int(f[2]),int(f[4]),f[5],d,b))
by=collections.defaultdict(dict)
for n,k,t,sol,d,b in rows: by[(n,k)][t]=(sol,d,b)
print("%-13s %5s %8s %8s %6s %s"%("N x K","T","default","best","gain","sol"))
for nk,ts in sorted(by.items()):
    for t in sorted(ts):
        sol,d,b=ts[t]
        print("%-13s %5d %8.3f %8.3f %6.2f %s"%("%dx%d"%nk,t,d,b,(d/b if b else 0), sol))
