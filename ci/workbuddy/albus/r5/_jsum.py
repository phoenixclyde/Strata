import subprocess, base64, re
def sh(s, t=150):
    p = subprocess.run(["ssh","-o","BatchMode=yes","-o","ConnectTimeout=10","albus@192.168.50.166","base64 -d | bash"],
                       input=base64.b64encode(s.encode()), stdout=subprocess.PIPE, stderr=subprocess.STDOUT, timeout=t)
    return p.stdout.decode("utf-8","replace")
f = sh("ls -t /home/albus/strata166/data/w795j_ab_*.txt 2>/dev/null | head -1").strip()
if not f: print("no file yet"); raise SystemExit
raw = sh("cat " + f)
cur=None; data={}
for ln in raw.splitlines():
    m = re.match(r"=== J=(\S+) ", ln)
    if m: cur=m.group(1); data[cur]=[]; continue
    if ln.startswith("=== RESTORE"): cur=None; continue
    if cur is None: continue
    if "MMQ tile:" in ln or ln.strip().startswith("[M] run1") or ln.startswith("strata prefill timing: 21822"):
        data[cur].append(ln)
print("FILE", f.split('/')[-1])
KEY=("gemm gate/up","gemm down","dequant","wait copy","gather","qsa attn","hc read","gdn")
print("%-5s %8s %8s %8s %8s %8s %8s %8s %8s" % ("J","prompt","GPU","gemmGU","gemmD","dequant","attn","hc","tile"))
for j, lines in data.items():
    tiles=[l.split("MMQ tile:")[1].strip() for l in lines if "MMQ tile:" in l]
    pm=[int(m.group(1)) for l in lines if (m:=re.search(r"prompt_ms=(\d+)", l))]
    ph=[l for l in lines if l.startswith("strata prefill timing: 21822")]
    gpu=[int(m.group(1)) for l in ph for m in [re.search(r"GPU timeline (\d+)", l)]]
    def g(k):
        return sum(int(m.group(1)) for l in ph for m in [re.search(re.escape(k)+r" (\d+) \(", l)])//max(1,len(ph))
    print("%-5s %8s %8s %8s %8s %8s %8s %8s %8s" % (
        j, pm[0] if pm else "-", gpu[0] if gpu else "-", g("gemm gate/up"), g("gemm down"), g("dequant"), g("qsa attn"), g("hc read"),
        "; ".join(tiles)[:60]))
