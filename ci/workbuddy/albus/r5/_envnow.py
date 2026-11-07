import subprocess, base64
def sh(s, t=90):
    p = subprocess.run(["ssh","-o","BatchMode=yes","-o","ConnectTimeout=10","albus@192.168.50.166","base64 -d | bash"],
                       input=base64.b64encode(s.encode()), stdout=subprocess.PIPE, stderr=subprocess.STDOUT, timeout=t)
    return p.stdout.decode("utf-8","replace")
print(sh(r'''
python3 - <<'PY'
import json
d = json.load(open('/home/albus/strata166/data/strata-huihui-ud-iq4_xs.json'))
print("env:", json.dumps(d.get('env', {}), ensure_ascii=False))
print("args:", json.dumps(d.get('args', d.get('argv', 'NA')), ensure_ascii=False)[:300])
print("keys:", sorted(d.keys()))
PY
docker ps --format "{{.Names}}|{{.Image}}|{{.Status}}" | grep strata166-407
curl -s --max-time 5 http://127.0.0.1:8090/health | head -c 60; echo
'''))
