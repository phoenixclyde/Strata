import subprocess, base64
def sh(s, t=300):
    p = subprocess.run(["ssh","-o","BatchMode=yes","-o","ConnectTimeout=10","albus@192.168.50.166","base64 -d | bash"],
                       input=base64.b64encode(s.encode()), stdout=subprocess.PIPE, stderr=subprocess.STDOUT, timeout=t)
    return p.stdout.decode("utf-8","replace")
print(sh("pkill -9 -f ab_p9.sh 2>/dev/null; sleep 2; pkill -9 -f mt_floor 2>/dev/null; sleep 1; ps -ef | grep -c '[a]b_p9'"))
print(sh(r'''python3 - <<'PY'
import json
p='/home/albus/strata166/data/strata-huihui-ud-iq4_xs.json'
d=json.load(open(p)); a=list(d.get('args') or [])
# 清掉孤立数值：不是 --conversation-cache-park-gain 的紧跟值，且是纯数字
out=[]; i=0; dropped=[]
while i < len(a):
    if a[i]=='--conversation-cache-park-gain':
        dropped.append(('pair', a[i:i+2])); i+=2; continue
    # 孤立数字：前一个元素不是需要取值的参数
    if a[i].isdigit() and (not out or not out[-1].startswith('--')):
        dropped.append(('stray', a[i])); i+=1; continue
    out.append(a[i]); i+=1
d['args']=out
json.dump(d, open(p,'w'), indent=2, ensure_ascii=False)
print('dropped', dropped)
print('tail', out[-8:])
PY''', t=120))
print(sh("docker restart strata166-407 >/dev/null 2>&1; for i in $(seq 1 300); do curl -s --max-time 2 http://127.0.0.1:8090/health >/dev/null 2>&1 && { echo ready=${i}s; break; }; sleep 1; done", t=340))
print(sh("curl -s --max-time 6 http://127.0.0.1:8090/metrics | python3 -c \"import sys,json;e=json.load(sys.stdin)['engine'];print('slots',e['expert_slots'],'vram',e['vram_free_mib'],'ver',e['version'])\"", t=120))
