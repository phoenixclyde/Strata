import subprocess, base64
def sh(s, t=120):
    p = subprocess.run(["ssh","-o","BatchMode=yes","-o","ConnectTimeout=10","albus@192.168.50.166","base64 -d | bash"],
                       input=base64.b64encode(s.encode()), stdout=subprocess.PIPE, stderr=subprocess.STDOUT, timeout=t)
    return p.stdout.decode("utf-8","replace")
print(sh(r'''curl -s --max-time 8 http://127.0.0.1:8090/metrics | python3 -c "
import sys,json
d=json.load(sys.stdin)
r=(d.get('requests') or [])
print('n_req',len(r))
if r: print('keys',sorted(r[0].keys())); print('row',json.dumps(r[0],ensure_ascii=False)[:400])
print('engine keys',sorted((d.get('engine') or {}).keys()))
"'''))
