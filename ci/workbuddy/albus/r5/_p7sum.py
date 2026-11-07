import subprocess, base64, re, os
def sh(s, t=180):
    p = subprocess.run(["ssh","-o","BatchMode=yes","-o","ConnectTimeout=10","albus@192.168.50.166","base64 -d | bash"],
                       input=base64.b64encode(s.encode()), stdout=subprocess.PIPE, stderr=subprocess.STDOUT, timeout=t)
    return p.stdout.decode("utf-8","replace")
f = sh("ls -t /home/albus/strata166/data/w797_ab_*.txt | head -1").strip()
print("FILE", f)
raw = sh("cat " + f)
os.makedirs(r"D:/workbuddy_space/strata_ws/albus/audit8/data", exist_ok=True)
open(r"D:/workbuddy_space/strata_ws/albus/audit8/data/w797_ab.txt","w",encoding="utf-8").write(raw)
arm=None; data={}
for ln in raw.splitlines():
    m = re.match(r"=== ARM ([A-E]) ", ln)
    if m: arm=m.group(1); data[arm]={}; continue
    if ln.startswith("=== RESTORE"): arm=None; continue
    m = re.match(r"strata prefill timing: (21822|99382) tokens, GPU timeline (\d+)", ln)
    if m and arm:
        def g(k):
            mm = re.search(re.escape(k) + r" (\d+) \(", ln)
            return int(mm.group(1)) if mm else None
        data[arm][("M" if m.group(1)=="21822" else "L")] = dict(
            gpu=int(m.group(2)), hc=g("hc read"), gu=g("gemm gate/up"), gd=g("gemm down"),
            attn=g("qsa attn"), gdn=g("gdn"), rec=g("gdn recurrence"), gop=g("gdn out proj"),
            qp=g("qsa proj"), sel=g("qsa select"), deq=g("dequant"), rt=g("router+shared"))
KEYS=[("gpu","GPU"),("gdn","gdn"),("rec","rec"),("gop","outproj"),("hc","hc"),
      ("gu","gemmGU"),("attn","attn"),("gd","gemmD"),("deq","dequant")]
for prof in ("M","L"):
    print("\n===== %s 档 ====="%prof)
    print("%-4s"%"arm" + "".join("%9s"%k[1] for k in KEYS))
    base = data.get("A",{}).get(prof,{})
    for a in "ABCDE":
        d = data.get(a,{}).get(prof)
        if not d: print(a,"MISSING"); continue
        print("%-4s"%a + "".join("%9s"%d[k] for k,_ in KEYS))
    if base:
        print("--- vs A (%) ---")
        for a in "ABCDE":
            d = data.get(a,{}).get(prof)
            if not d or a=="A": continue
            print("%-4s"%a + "".join("%9s"%("%+.2f"%((d[k]/base[k]-1)*100) if base.get(k) and d.get(k) else "-") for k,_ in KEYS))
print("\n=== needle / 收尾 ===")
for ln in raw.splitlines():
    if "FOUND" in ln or ln.startswith("=== RESTORE") or "env_final" in ln or "slots" in ln:
        print("  ", ln[:150])
