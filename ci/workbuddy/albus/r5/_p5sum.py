import subprocess, base64, re
def sh(s, t=120):
    p = subprocess.run(["ssh","-o","BatchMode=yes","-o","ConnectTimeout=10","albus@192.168.50.166","base64 -d | bash"],
                       input=base64.b64encode(s.encode()), stdout=subprocess.PIPE, stderr=subprocess.STDOUT, timeout=t)
    return p.stdout.decode("utf-8","replace")
f = sh("ls -t /home/albus/strata166/data/w795_ab_*.txt | head -1").strip()
raw = sh("cat " + f)
print("FILE", f.split('/')[-1])
# group sort / mmq markers
for ln in raw.splitlines():
    if "MMQ sorts" in ln or "MMQ reads" in ln or "no tile for" in ln:
        print("MARK:", ln[:150])
arm=None; rows=[]
for ln in raw.splitlines():
    m=re.match(r"=== ARM ([ABC]) ", ln)
    if m: arm=m.group(1); continue
    if ln.strip().startswith("[M] run1"):
        q=re.search(r"prompt_ms=(\d+)", ln); rows.append([arm, int(q.group(1))]); continue
    if "21822 tokens" in ln or "21827 tokens" in ln:
        pass
    if ln.startswith("strata prefill timing"):
        pass
print("runs:", rows)
# phase lines
ph={}
arm=None
for ln in raw.splitlines():
    m=re.match(r"=== ARM ([ABC]) ", ln)
    if m: arm=m.group(1); continue
    if ln.startswith("strata prefill timing"):
        kv=dict(re.findall(r"([a-z+/ ]+?) (\d+) \(", ln))
        tot=re.search(r"GPU timeline (\d+)", ln)
        ph.setdefault(arm, []).append((int(tot.group(1)) if tot else 0, kv))
for a in ("A","B","C"):
    for tot, kv in ph.get(a, []):
        print(a, "GPU", tot, {k:kv[k] for k in ("hc read","gemm gate/up","gemm down","qsa attn","gdn","dequant") if k in kv})
