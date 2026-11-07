import subprocess, base64, re
def sh(s, t=90):
    p = subprocess.run(["ssh","-o","BatchMode=yes","-o","ConnectTimeout=10","albus@192.168.50.166","base64 -d | bash"],
                       input=base64.b64encode(s.encode()), stdout=subprocess.PIPE, stderr=subprocess.STDOUT, timeout=t)
    return p.stdout.decode("utf-8","replace")
f = sh("ls -t /home/albus/strata166/data/w793b_ab_*.txt | head -1").strip()
raw = sh("cat " + f)
arm=None; rows=[]
for ln in raw.splitlines():
    m=re.match(r'=== ARM ([ABC]) ', ln)
    if m: arm=m.group(1); continue
    if "21822 tokens" in ln:
        kv=dict(re.findall(r'([a-z+/ ]+?) ([\d.]+) \(', ln))
        tot=re.search(r'GPU timeline (\d+) ms, wall (\d+)', ln)
        rows.append((arm, int(tot.group(1)), kv.get('hc read'), kv.get('gdn'), kv.get('qsa attn'), kv.get('gemm gate/up')))
    if ln.startswith("  [M] run1"):
        pt=re.search(r'prompt_ms=(\d+)', ln); rows[-1]=rows[-1]+(int(pt.group(1)),) if pt else rows[-1]
print(f)
print("%-3s %8s %8s %8s %8s %8s %8s"%("arm","GPUms","hc read","gdn","qsa attn","gemmGU","prompt_ms"))
for r in rows:
    print("%-3s %8s %8s %8s %8s %8s %8s"%(r[0], r[1], r[2], r[3], r[4], r[5], r[6] if len(r)>6 else "-"))
