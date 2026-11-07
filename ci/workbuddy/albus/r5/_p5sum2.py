import subprocess, base64, re
def sh(s, t=120):
    p = subprocess.run(["ssh","-o","BatchMode=yes","-o","ConnectTimeout=10","albus@192.168.50.166","base64 -d | bash"],
                       input=base64.b64encode(s.encode()), stdout=subprocess.PIPE, stderr=subprocess.STDOUT, timeout=t)
    return p.stdout.decode("utf-8","replace")
f = sh("ls -t /home/albus/strata166/data/w795_ab_*.txt | head -1").strip()
raw = sh("cat " + f)
print("runs:", [ (m.group(1), m.group(2)) for m in re.finditer(r"=== ARM ([ABC]) [^\n]*|\[M\] run1[^\n]*prompt_ms=(\d+)", raw)][:20])
lines = [l for l in raw.splitlines() if l.startswith("strata prefill timing")]
print("timing lines:", len(lines))
for l in lines[:2]: print("SAMPLE:", l[:600])
print("groupsort markers:", [l[:120] for l in raw.splitlines() if "MMQ" in l and ("sort" in l or "reads" in l or "tile" in l)])
