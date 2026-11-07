import subprocess, base64, re
def sh(s, t=120):
    p = subprocess.run(["ssh","-o","BatchMode=yes","-o","ConnectTimeout=10","albus@192.168.50.166","base64 -d | bash"],
                       input=base64.b64encode(s.encode()), stdout=subprocess.PIPE, stderr=subprocess.STDOUT, timeout=t)
    return p.stdout.decode("utf-8","replace")
f = sh("ls -t /home/albus/strata166/data/w795_ab_*.txt | head -1").strip()
raw = sh("cat " + f)
arm=None; run=-1; data={}
for ln in raw.splitlines():
    m=re.match(r"=== ARM ([ABC]) ", ln)
    if m:
        arm=m.group(1); run+=1; data[(arm,run)]=[]; continue
    m=re.match(r"strata prefill timing: (\d+) tokens, GPU timeline (\d+) ms", ln)
    if m and arm and data:
        data[(arm,run)].append((int(m.group(1)), int(m.group(2)), ln))
for k in sorted(data, key=lambda x:(x[0],x[1])):
    runs=data[k]
    print(k, [(t,g) for t,g,_ in runs])
KEY=("hc read","gemm gate/up","gemm down","dequant","wait copy","qsa attn","gdn","gather")
print("=== aggregated 8192 chunks ===")
for a in ("A","B","C"):
    agg={}; tot=0; n=0
    for k in data:
        if k[0]!=a: continue
        for t,g,ln in data[k]:
            if t!=8192: continue
            n+=1; tot+=g
            for kk in KEY:
                m=re.search(re.escape(kk)+r" (\d+) \(", ln)
                if m: agg[kk]=agg.get(kk,0)+int(m.group(1))
    print(a, "n=",n, "GPU", tot, {kk:agg.get(kk,0) for kk in KEY})
print("=== prod ===")
print(sh("""docker ps --format "{{.Names}}|{{.Image}}|{{.Status}}" | grep strata166-407
curl -s --max-time 5 http://127.0.0.1:8090/health | head -c 60; echo
python3 -c "import json;print(sorted(json.load(open('/home/albus/strata166/data/strata-huihui-ud-iq4_xs.json')).get('env',{}).items()))"
tail -3 /home/albus/strata166/data/w795_ab_*.txt"""))
