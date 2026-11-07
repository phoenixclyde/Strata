# -*- coding: utf-8 -*-
"""166：PLE I/O 模式的 A/B —— direct(现状) / mmap / ram 三个 arm"""
import base64, os, subprocess

KEY = os.path.expanduser('~/.ssh/id_ed25519_workbuddy')
SSH = r'C:\Program Files\Git\usr\bin\ssh.exe'
HOST = 'albus@192.168.50.166'

SCRIPT = r'''
set +e
CONF=/data/strata-ud-q4_k_xl.json

cat > /home/albus/strata166/data/setarg.py <<'PYEOF'
import json, pathlib, sys
p = pathlib.Path('/data/strata-ud-q4_k_xl.json')
cfg = json.loads(p.read_text())
a = cfg['args']
# 先清掉所有 --ple-io / --ple-inflight / --ple-row-cache
def strip(flag):
    while flag in a:
        i = a.index(flag)
        del a[i:i+2]
for f in ('--ple-io', '--ple-inflight', '--ple-row-cache'):
    strip(f)
mode = sys.argv[1] if len(sys.argv) > 1 else 'direct'
if mode != 'direct':
    a += ['--ple-io', mode]
p.write_text(json.dumps(cfg, indent=1))
cfg = json.loads(p.read_text())
print('CONF ple-io =>', ' '.join(str(x) for x in cfg['args']))
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
print('RESULT %s prompt=%s wall=%.2fs tol=%.1f tok/s  (ms/token=%.2f)'
      % (tag, pt, te-t0, pt/(te-t0) if pt else -1, (te-t0)*1000/pt if pt else -1))
sys.stdout.flush()
PYEOF

arm () {
  MODE="$1"
  echo ""
  echo "############ ARM ple-io=$MODE ############"
  docker exec strata166 python3 /data/setarg.py "$MODE"
  for p in $(docker exec strata166 bash -lc 'ps -eo pid,args | grep -E "serve/server\.py|build-906/strata" | grep -v grep | awk "{print \$1}"'); do
    docker exec strata166 bash -lc "kill -9 $p" 2>/dev/null
  done
  sleep 4
  docker exec strata166 bash -lc 'free -g | head -2; echo "--- memlock ---"; prlimit --pid $(pgrep -f "serve/[s]erver.py" | head -1) 2>/dev/null | grep -i memlock || echo "(无进程)"'
  docker exec strata166 bash -lc "cd /src && setsid nohup python3 serve/server.py --engine strata --config $CONF --port 8090 > /data/serve-run.log 2>&1 < /dev/null & echo started"
  for i in $(seq 1 24); do
    sleep 20
    if docker exec strata166 bash -lc 'grep -q "ready: http" /data/serve-run.log 2>/dev/null'; then echo "[$MODE ready @ $((i*20))s]"; break; fi
    if ! docker exec strata166 bash -lc 'ps -eo args | grep -q "[s]erve/server.py"'; then echo "[$MODE 启动失败]"; docker exec strata166 bash -lc 'tail -14 /data/serve-run.log; echo ---; tail -8 /data/strata-ud-q4_k_xl.log'; return; fi
  done
  docker exec strata166 bash -lc 'grep -iE "ple|PLE" /data/strata-ud-q4_k_xl.log | tail -4'
  docker exec strata166 python3 /data/ab.py "$MODE" 2>&1 | tail -2
  docker exec strata166 bash -lc 'grep -E "prompt [0-9]+ tokens" /data/strata-ud-q4_k_xl.log | tail -1; echo; free -g | head -2'
}

arm direct
arm mmap
arm ram
echo ""
echo "############ 收尾：复原 direct ############"
arm direct
docker exec strata166 bash -lc 'curl -s -m 10 http://127.0.0.1:8090/v1/models; echo'
'''

b64 = base64.b64encode(SCRIPT.encode('utf-8')).decode('ascii')
cmd = [SSH, '-o', 'BatchMode=yes', '-o', 'ConnectTimeout=10', '-o', 'ServerAliveInterval=30',
       '-i', KEY, HOST, 'base64 -d | bash']
r = subprocess.run(cmd, input=b64.encode('ascii'), capture_output=True, timeout=7200)
with open(r'D:\strata166\logs\_ab_pleio.txt', 'w', encoding='utf-8') as f:
    f.write(r.stdout.decode('utf-8', 'replace'))
    if r.stderr.strip():
        f.write('\n--- STDERR ---\n' + r.stderr.decode('utf-8', 'replace')[:600])
print('done -> D:\\strata166\\logs\\_ab_pleio.txt')
