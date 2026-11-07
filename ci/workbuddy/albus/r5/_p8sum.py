import subprocess, base64, re, os
def sh(s, t=180):
    p = subprocess.run(["ssh","-o","BatchMode=yes","-o","ConnectTimeout=10","albus@192.168.50.166","base64 -d | bash"],
                       input=base64.b64encode(s.encode()), stdout=subprocess.PIPE, stderr=subprocess.STDOUT, timeout=t)
    return p.stdout.decode("utf-8","replace")
f = sh("ls -t /home/albus/strata166/data/w798d_phase_*.txt 2>/dev/null | head -1").strip()
if not f: print("no file"); raise SystemExit
print("FILE", f.split('/')[-1])
raw = sh("cat " + f)
open(r"D:/workbuddy_space/strata_ws/albus/audit8/data/w798d.txt","w",encoding="utf-8").write(raw)
arm=None; data={}
for ln in raw.splitlines():
    m = re.match(r"=== ARM ([A-E]) ", ln)
    if m: arm=m.group(1); data[arm]=[]; continue
    if ln.startswith("=== RESTORE") or ln.startswith("=== DONE"): arm=None; continue
    if "decode GPU stages" in ln and arm:
        # 只取 GDN 段（第一个 "| QSA layers" 之前）
        head = ln.split("| QSA layers")[0]
        pairs = re.findall(r"([a-zA-Z0-9+/&\- ]+?) ([\d.]+)(?=\s|$)", head)
        d = {}
        for k, v in pairs:
            d[k.strip()] = float(v)
        qsa = ln.split("| QSA layers")[1] if "| QSA layers" in ln else ""
        for k, v in re.findall(r"([a-zA-Z0-9+/&\- ]+?) ([\d.]+)(?=\s|$)", qsa):
            d["Q:" + k.strip()] = float(v)
        data[arm].append(d)
KEYS = ["q8+qkv/q-idx gemv", "rec", "out-proj", "router+plan+bell", "shared+quant",
        "waitA", "VRAM hits", "waitB", "PCIe grp", "waitCPU", "copy+combine", "(gap)",
        "Q:q+q-idx", "Q:scores+topk", "Q:attention", "Q:VRAM hits", "Q:shared+quant", "Q:waitA"]
print("%-22s" % "phase" + "".join("%9s" % a for a in "ACDE"))
med = {}
for k in KEYS:
    row = []
    for a in "ACDE":
        vals = [d[k] for d in data.get(a, [])[1:] if k in d]   # 跳过首轮
        row.append(sorted(vals)[len(vals)//2] if vals else None)
        med[(a, k)] = row[-1]
    if row[0] is None: continue
    print("%-22s" % k + "".join("%9.2f" % v if v is not None else "%9s" % "-" for v in row))
print("\n--- vs A (%) ---")
print("%-22s" % "phase" + "".join("%9s" % a for a in "CDE"))
for k in KEYS:
    base = med.get(("A", k))
    if not base: continue
    cells = []
    for a in "CDE":
        v = med.get((a, k))
        cells.append("%+8.1f" % ((v / base - 1) * 100) if v else "%9s" % "-")
    if all(c.strip() in ("-", "+0.0") for c in cells): continue
    print("%-22s" % k + "".join("%9s" % c for c in cells))
print("\n--- 端到端（每臂 r1-r4 decode_ms）---")
arm=None
for ln in raw.splitlines():
    m = re.match(r"=== ARM ([A-E]) ", ln)
    if m: arm=m.group(1); print("\n%s: " % arm, end=""); continue
    if ln.startswith("  r") and arm: print(ln.strip().replace("decode_ms=", "") + " | ", end="")
print()
print("\n--- needle/收尾 ---")
for ln in raw.splitlines():
    if "env_final" in ln or ln.startswith("=== DONE") or "slots" in ln: print("  ", ln[:160])
