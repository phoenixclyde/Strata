# -*- coding: utf-8 -*-
"""166：MMQ / KQ256 三个单变量 A/B + 复原基线。固定 21589-token prompt 测预填。"""
import base64, os, subprocess

KEY = os.path.expanduser('~/.ssh/id_ed25519_workbuddy')
SSH = r'C:\Program Files\Git\usr\bin\ssh.exe'
HOST = 'albus@192.168.50.166'

SCRIPT = r'''
set +e
CONF=/data/strata-ud-q4_k_xl.json
BENCH=/data/ab.py
cat > /home/albus/strata166/data/ab.py <<'PYEOF'
import json, sys, time, urllib.request
BASE='http://127.0.0.1:8090/v1'
mdl=json.loads(urllib.request.urlopen(BASE+'/models',timeout=60).read().decode())['data'][0]['id']
PARA=("The principal advantage of the configuration under test is that its working set fits "
      "entirely inside the memory hierarchy of the machine, so the steady state needs no disk "
      "access at all and the throughput is limited by compute rather than by storage. ")
tag=sys.argv[1] if len(sys.argv)>1 else '?'
text=PARA*400
text=("Read the following text and answer with exactly one sentence.\n\n"+text+"\n\nQuestion: what is the principal advantage described?")
payload={'model':mdl,'messages':[{'role':'user','content':text}],'max_tokens':64,
         'temperature':0.0,'stream':True,'stream_options':{'include_usage':True}}
req=urllib.request.Request(BASE+'/chat/completions',data=json.dumps(payload).encode(),
                           headers={'Content-Type':'application/json'})
t0=time.time(); tf=None; usage=None
with urllib.request.urlopen(req,timeout=3600) as r:
    for raw in r:
        line=raw.decode('utf-8','replace').strip()
        if not line.startswith('data:'): continue
        d=line[5:].strip()
        if d=='[DONE]': break
        try: j=json.loads(d)
        except Exception: continue
        if j.get('usage'): usage=j['usage']
        for ch in (j.get('choices') or []):
            dc=ch.get('delta') or {}
            if dc.get('content') or dc.get('reasoning_content'):
                if tf is None: tf=time.time()
te=time.time()
pt=(usage or {}).get('prompt_tokens'); ct=(usage or {}).get('completion_tokens')
print('RESULT %s prompt=%s completion=%s TTFT=%.2fs prefill=%.1f tok/s decode=%.2f tok/s'
      % (tag, pt, ct, (tf-t0) if tf else -1,
         (pt/(tf-t0)) if pt and tf else -1,
         ((ct-1)/(te-tf)) if ct and tf and te>tf else -1))
sys.stdout.flush()
PYEOF

arm () {
  NAME="$1"; shift
  echo ""
  echo "############ ARM: $NAME (env: $*) ############"
  for p in $(docker exec strata166 bash -lc 'ps -eo pid,args | grep -E "serve/server\.py|build-906/strata" | grep -v grep | awk "{print \$1}"'); do
    docker exec strata166 bash -lc "kill -9 $p" 2>/dev/null
  done
  sleep 4
  docker exec strata166 bash -lc 'ps -eo pid,args | grep -E "serve/server\.py|build-906/strata" | grep -v grep | head -3; echo "(空=干净)"'
  ENVARGS=""
  for e in "$@"; do ENVARGS="$ENVARGS -e $e"; done
  docker exec $ENVARGS strata166 bash -lc "cd /src && setsid nohup python3 serve/server.py --engine strata --config $CONF --port 8090 > /data/serve-run.log 2>&1 < /dev/null & echo started"
  for i in $(seq 1 20); do
    sleep 20
    if docker exec strata166 bash -lc 'grep -q "ready: http" /data/serve-run.log 2>/dev/null'; then echo "[$NAME ready @ $((i*20))s]"; break; fi
    if ! docker exec strata166 bash -lc 'ps -eo args | grep -q "[s]erve/server.py"'; then echo "[$NAME 启动失败]"; docker exec strata166 bash -lc 'tail -12 /data/serve-run.log; tail -6 /data/strata-ud-q4_k_xl.log'; return; fi
  done
  docker exec strata166 python3 /data/ab.py "$NAME" 2>&1 | tail -3
  docker exec strata166 bash -lc 'grep -E "prompt [0-9]+ tokens" /data/strata-ud-q4_k_xl.log | tail -1'
}

arm baseline
arm kq256    STRATA_KQ256=1
arm mmq_off  STRATA_PREFILL_MMQ=0
arm restore
echo ""
echo "############ 收尾状态 ############"
docker exec strata166 bash -lc 'curl -s -m 10 http://127.0.0.1:8090/v1/models; echo'
docker exec strata166 bash -lc 'egrep "prompt [0-9]+ tokens|expert cache hit rate" /data/strata-ud-q4_k_xl.log | tail -8'
'''

b64 = base64.b64encode(SCRIPT.encode('utf-8')).decode('ascii')
cmd = [SSH, '-o', 'BatchMode=yes', '-o', 'ConnectTimeout=10', '-o', 'ServerAliveInterval=30',
       '-i', KEY, HOST, 'base64 -d | bash']
r = subprocess.run(cmd, input=b64.encode('ascii'), capture_output=True, timeout=5400)
with open(r'D:\strata166\logs\_ab_mmq.txt', 'w', encoding='utf-8') as f:
    f.write(r.stdout.decode('utf-8', 'replace'))
    if r.stderr.strip():
        f.write('\n--- STDERR ---\n' + r.stderr.decode('utf-8', 'replace')[:600])
print('done -> D:\\strata166\\logs\\_ab_mmq.txt')
