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
    if m: arm=m.group(1); run+=1; data[(arm,run)]=[]; continue
    m=re.match(r"strata prefill timing: (\d+) tokens, GPU timeline (\d+) ms", ln)
    if m and arm and data: data[(arm,run)].append((int(m.group(1)), int(m.group(2)), ln))
KEY=("hc read","gemm gate/up","gemm down","dequant","wait copy","qsa attn","gdn","qsa proj","gdn out proj","router+shared","qsa select","gdn recurrence","gather")
agg={}
for a in ("A","B","C"):
    agg[a]={}; tots=[]
    for k in data:
        if k[0]!=a: continue
        for t,g,ln in data[k]:
            if t!=21822: continue
            tots.append(g)
            for kk in KEY:
                m=re.search(re.escape(kk)+r" (\d+) \(", ln)
                if m: agg[a][kk]=agg[a].get(kk,0)+int(m.group(1))
    agg[a]["__n"]=len(tots); agg[a]["__gpu"]=sum(tots)
print("%-16s %8s %8s %8s" % ("phase", "A", "B", "B/A"))
for kk in KEY+("__gpu",):
    a=agg["A"].get(kk,0)/max(1,agg["A"]["__n"]); b=agg["B"].get(kk,0)/max(1,agg["B"]["__n"]); c=agg["C"].get(kk,0)/max(1,agg["C"]["__n"])
    print("%-16s %8.0f %8.0f %8.3f   (C %.0f)" % (kk, a, b, (b/a if a else 0), c))
print("n runs:", {a:agg[a]["__n"] for a in agg})
