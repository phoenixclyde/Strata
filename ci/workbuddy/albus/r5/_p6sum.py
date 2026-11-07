import subprocess, base64, re
def sh(s, t=150):
    p = subprocess.run(["ssh","-o","BatchMode=yes","-o","ConnectTimeout=10","albus@192.168.50.166","base64 -d | bash"],
                       input=base64.b64encode(s.encode()), stdout=subprocess.PIPE, stderr=subprocess.STDOUT, timeout=t)
    return p.stdout.decode("utf-8","replace")
f = sh("ls -t /home/albus/strata166/data/w796_ab_*.txt | head -1").strip()
raw = sh("cat " + f)
arm = None
print("FILE", f.split('/')[-1])
print("%-3s %-3s %8s %8s %8s %8s %8s %8s %8s" % ("arm","prf","GPU","attn","select","hc","GU","gdn","qsa_proj"))
for ln in raw.splitlines():
    m = re.match(r"=== ARM ([ABC]) ", ln)
    if m: arm = m.group(1); continue
    m = re.match(r"strata prefill timing: (21822|99382) tokens, GPU timeline (\d+)", ln)
    if not m: continue
    def g(k):
        mm = re.search(re.escape(k) + r" (\d+) \(", ln)
        return int(mm.group(1)) if mm else -1
    prf = "M" if m.group(1) == "21822" else "L"
    print("%-3s %-3s %8s %8s %8s %8s %8s %8s %8s" % (arm, prf, m.group(2), g("qsa attn"), g("qsa select"),
          g("hc read"), g("gemm gate/up"), g("gdn"), g("qsa proj")))
print("--- 进度 ---")
print(sh("ps -ef | grep -c '[a]b_p6.sh'; tail -3 " + f + " | cut -c1-90"))
