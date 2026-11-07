import subprocess, base64
def sh(s, t=120):
    p = subprocess.run(["ssh","-o","BatchMode=yes","-o","ConnectTimeout=10","albus@192.168.50.166","base64 -d | bash"],
                       input=base64.b64encode(s.encode()), stdout=subprocess.PIPE, stderr=subprocess.STDOUT, timeout=t)
    return p.stdout.decode("utf-8","replace")
print(sh(r'''
P=/home/albus/strata166/data/packs/huihui-ud-iq4_xs
echo "=== index.txt 前 12 行 ==="
head -12 "$P/index.txt" | cut -c1-200
echo "=== native_experts.txt 头 3 行 + 行数 ==="
head -3 "$P/native_experts.txt" | cut -c1-160; wc -l "$P/native_experts.txt"
echo "=== conversions.json 里的 geometry 键 ==="
python3 - <<'PY'
import json
d = json.load(open('/home/albus/strata166/data/packs/huihui-ud-iq4_xs/conversions.json'))
if isinstance(d, dict):
    ks = list(d.keys())[:12]
    print("keys:", ks)
    for k in ks:
        v = d[k]
        print(" ", k, str(v)[:120])
PY
'''))
