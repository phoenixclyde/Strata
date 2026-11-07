import subprocess, base64, re
def sh(s, t=180):
    p = subprocess.run(["ssh","-o","BatchMode=yes","-o","ConnectTimeout=10","albus@192.168.50.166","base64 -d | bash"],
                       input=base64.b64encode(s.encode()), stdout=subprocess.PIPE, stderr=subprocess.STDOUT, timeout=t)
    return p.stdout.decode("utf-8","replace")
f = sh("ls -t /home/albus/strata166/data/w798e_phase_*.txt 2>/dev/null | head -1").strip()
if not f: print("no file yet"); raise SystemExit
raw = sh("cat " + f)
open(r"D:/workbuddy_space/strata_ws/albus/audit8/data/w798e.txt","w",encoding="utf-8").write(raw)
arm=None; data={}
for ln in raw.splitlines():
    m = re.match(r"=== ARM ([A-E]) ", ln)
    if m: arm=m.group(1); data[arm]=[]; continue
    if ln.startswith("=== RESTORE") or ln.startswith("=== DONE"): arm=None; continue
    if "decode GPU stages" in ln and arm:
        head, _, qsa = ln.partition("| QSA layers")
        d = {k.strip(): float(v) for k, v in re.findall(r"([a-zA-Z0-9+/&\- ]+?) ([\d.]+)(?=\s|$)", head)}
        for k, v in re.findall(r"([a-zA-Z0-9+/&\- ]+?) ([\d.]+)(?=\s|$)", qsa):
            d["Q:" + k.strip()] = float(v)
        data[arm].append(d)
KEYS = ["q8+qkv/q-idx gemv", "rec", "out-proj", "router+plan+bell", "shared+quant", "VRAM hits",
        "waitA", "waitB", "PCIe grp", "waitCPU", "copy+combine", "Q:q+q-idx", "Q:attention", "Q:VRAM hits"]
print("FILE", f.split('/')[-1])
print("%-22s" % "phase" + "".join("%9s" % a for a in "ABCD"))
med = {}
for k in KEYS:
    row = []
    for a in "ABCD":
        vals = [d[k] for d in data.get(a, [])[1:] if k in d]
        row.append(sorted(vals)[len(vals)//2] if vals else None)
        med[(a, k)] = row[-1]
    if row[0] is None: continue
    print("%-22s" % k + "".join("%9.2f" % v if v is not None else "%9s" % "-" for v in row))
print("\n--- vs A (%) ---  B=GDN_SPLIT C=TSUM D=QFUSE")
print("%-22s" % "phase" + "".join("%9s" % a for a in "BCD"))
for k in KEYS:
    base = med.get(("A", k))
    if not base: continue
    cells = []
    for a in "BCD":
        v = med.get((a, k))
        cells.append("%+8.1f" % ((v / base - 1) * 100) if v else "%9s" % "-")
    if all(c.strip() == "-" or c.strip() in ("+0.0", "-0.0") for c in cells): continue
    print("%-22s" % k + "".join("%9s" % c for c in cells))
print("\n--- 端到端 decode_ms ---")
arm=None
for ln in raw.splitlines():
    m = re.match(r"=== ARM ([A-E]) ", ln)
    if m: arm=m.group(1); print("%s: " % arm, end=""); continue
    if ln.startswith("  r") and arm:
        mm = re.search(r"decode_ms=([\d.]+)", ln)
        if mm: print("%.0f " % float(mm.group(1)), end="")
print()
for ln in raw.splitlines():
    if "env_final" in ln or ln.startswith("=== DONE") or ln.startswith("=== RESTORE"): print("  ", ln[:150])
