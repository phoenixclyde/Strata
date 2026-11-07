# -*- coding: utf-8 -*-
"""166：第四轮修正版 —— --prefill 必留（serve 硬要求）、--ple-inflight <= 1024、加前置断言"""
import base64, os, subprocess

KEY = os.path.expanduser('~/.ssh/id_ed25519_workbuddy')
SSH = r'C:\Program Files\Git\usr\bin\ssh.exe'
HOST = 'albus@192.168.50.166'

SCRIPT = r'''
set +e
CONF=/data/strata-ud-q4_k_xl.json

cat > /home/albus/strata166/data/setarg3.py <<'PYEOF'
import json, pathlib, sys
p = pathlib.Path('/data/strata-ud-q4_k_xl.json')
cfg = json.loads(p.read_text())
a = cfg['args']
OPT = ('--ple-io', '--ple-inflight', '--ple-row-cache', '--pcie-frac', '--adapt-every')
REQ = ('--prefill',)          # serve 硬要求，永远保留（auto 合法）
for f in OPT + REQ:
    while f in a:
        i = a.index(f)
        del a[i:i+2]
kv = {}
rest = sys.argv[1:]
for i in range(0, len(rest), 2):
    kv[rest[i]] = rest[i+1]
for f in REQ:
    a += [f, kv.get(f, 'auto')]      # 永远带上
for f in OPT:
    v = kv.get(f)
    if v and v != 'DEFAULT':
        a += [f, v]
# --- 前置断言（fail-closed，防自己再写出非法配置）---
assert '--prefill' in a and a[a.index('--prefill')+1], 'prefill 必填'
if '--ple-inflight' in a:
    n = int(a[a.index('--ple-inflight')+1]); assert 1 <= n <= 1024, 'ple-inflight 越界: %d' % n
if '--pcie-frac' in a:
    float(a[a.index('--pcie-frac')+1])
p.write_text(json.dumps(cfg, indent=1))
print('CONF OK =>', ' '.join(str(x) for x in json.loads(p.read_text())['args']))
PYEOF

cat > /home/albus/strata166/data/ab.py <<'PYEOF'
import json, sys, time, urllib.request
BASE='http://127.0.0.1:8090/v1'
mdl=json.loads(urllib.request.urlopen(BASE+'/models',timeout=60).read().decode())['data'][0]['id']
PARA=("The principal advantage of the configuration under test is that its working set fits "
      "entirely inside the memory hierarchy of the machine, so the steady state needs no disk "
      "access at all and the throughput is limited by compute rather than by storage. ")
tag=sys.argv[1] if len(sys.argv)>1 else '?'
text=("Read the following text and answer with exactly one sentence.\n\n"+PARA*400+
      "\n\nQuestion: what is the principal advantage described?")
payload={'model':mdl,'messages':[{'role':'user','content':text}],'max_tokens':64,
         'temperature':0.0,'stream':True,'stream_options':{'include_usage':True}}
req=urllib.request.Request(BASE+'/chat/completions',data=json.dumps(payload).encode(),
                           headers={'Content-Type':'application/json'})
t0=time.time(); usage=None
with urllib.request.urlopen(req,timeout=3600) as r:
    for raw in r:
        line=raw.decode('utf-8','replace').strip()
        if not line.startswith('data:'):
            continue
        d=line[5:].strip()
        if d=='[DONE]': break
        try: j=json.loads(d)
        except Exception: continue
        if j.get('usage'): usage=j['usage']
te=time.time()
pt=(usage or {}).get('prompt_tokens')
print('RESULT %s prompt=%s wall=%.2fs tol=%.1f tok/s' % (tag, pt, te-t0, pt/(te-t0) if pt else -1))
sys.stdout.flush()
PYEOF

arm () {
  NAME="$1"; shift
  echo ""
  echo "############ ARM $NAME ############"
  if ! docker exec strata166 python3 /data/setarg3.py "$@"; then echo "[$NAME 配置被断言拦下，跳过]"; return; fi
  for p in $(docker exec strata166 bash -lc 'ps -eo pid,args | grep -E "serve/server\.py|build-906/strata" | grep -v grep | awk "{print \$1}"'); do
    docker exec strata166 bash -lc "kill -9 $p" 2>/dev/null
  done
  sleep 4
  docker exec strata166 bash -lc "cd /src && setsid nohup python3 serve/server.py --engine strata --config $CONF --port 8090 > /data/serve-run.log 2>&1 < /dev/null & echo started"
  for i in $(seq 1 22); do
    sleep 20
    if docker exec strata166 bash -lc 'grep -q "ready: http" /data/serve-run.log 2>/dev/null'; then echo "[$NAME ready @ $((i*20))s]"; break; fi
    if ! docker exec strata166 bash -lc 'ps -eo args | grep -q "[s]erve/server.py"'; then echo "[$NAME 启动失败]"; docker exec strata166 bash -lc 'tail -6 /data/strata-ud-q4_k_xl.log'; return; fi
  done
  docker exec strata166 python3 /data/ab.py "$NAME" 2>&1 | tail -2
  docker exec strata166 bash -lc 'grep -E "prompt [0-9]+ tokens = 0 reused" /data/strata-ud-q4_k_xl.log | tail -1'
}

arm baseline        --prefill auto --ple-inflight DEFAULT --pcie-frac DEFAULT --adapt-every DEFAULT
arm ple_inflight1024 --prefill auto --ple-inflight 1024    --pcie-frac DEFAULT --adapt-every DEFAULT
arm pcie_zero       --prefill auto --ple-inflight DEFAULT --pcie-frac 0.0     --adapt-every DEFAULT
arm adapt_every0    --prefill auto --ple-inflight DEFAULT --pcie-frac DEFAULT --adapt-every 0
arm restore         --prefill auto --ple-inflight DEFAULT --pcie-frac DEFAULT --adapt-every DEFAULT
echo ""
echo "############ 最终状态 ############"
docker exec strata166 bash -lc 'python3 -c "
import json;a=json.load(open(\"/data/strata-ud-q4_k_xl.json\"))[\"args\"];print(\" \".join(map(str,a)))"'
docker exec strata166 bash -lc 'curl -s -m 10 http://127.0.0.1:8090/v1/models; echo'
'''

b64 = base64.b64encode(SCRIPT.encode('utf-8')).decode('ascii')
cmd = [SSH, '-o', 'BatchMode=yes', '-o', 'ConnectTimeout=10', '-o', 'ServerAliveInterval=30',
       '-i', KEY, HOST, 'base64 -d | bash']
r = subprocess.run(cmd, input=b64.encode('ascii'), capture_output=True, timeout=9000)
with open(r'D:\strata166\logs\_ab_round5.txt', 'w', encoding='utf-8') as f:
    f.write(r.stdout.decode('utf-8', 'replace'))
    if r.stderr.strip():
        f.write('\n--- STDERR ---\n' + r.stderr.decode('utf-8', 'replace')[:600])
print('done -> D:\\strata166\\logs\\_ab_round5.txt')
