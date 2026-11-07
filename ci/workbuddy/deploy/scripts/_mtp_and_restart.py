# -*- coding: utf-8 -*-
"""166：生成 MTP draft 层 -> 配置里补 --mtp -> 重启 serve -> 轮询到 ready。"""
import base64, os, subprocess

KEY = os.path.expanduser('~/.ssh/id_ed25519_workbuddy')
SSH = r'C:\Program Files\Git\usr\bin\ssh.exe'
HOST = 'albus@192.168.50.166'

SCRIPT = r'''
set +e
echo "=== 1) 生成 MTP draft 层 ==="
docker exec strata166 bash -lc '
cd /src
export STRATA_GGUF_PY=/src/third_party/llama.cpp/gguf-py
echo "--- mtp_pack ---"
python3 tools/mtp_pack.py --src /data/mtp --experts q2_0 --out /data/mtp/mtp-q2_0.gguf 2>&1 | tail -6
echo "mtp_pack rc=$?"
echo "--- mtp_rt ---"
python3 tools/mtp_rt.py --gguf /data/mtp/mtp-q2_0.gguf --out /data/mtp/rt 2>&1 | tail -4
echo "mtp_rt rc=$?"
cp -f /src/data/draft_vocab.bin /data/mtp/rt/ 2>&1
echo "--- rt 内容 ---"; ls -l /data/mtp/rt
'
echo
echo "=== 2) 配置补 --mtp ==="
docker exec strata166 bash -lc 'python3 - <<PYEOF
import json
p="/data/strata-ud-q4_k_xl.json"
c=json.load(open(p))
a=c["args"]
if "--mtp" not in a:
    i=a.index("--spec-min-p")+2
    a[i:i]=["--mtp","/data/mtp/rt"]
json.dump(c,open(p,"w"),indent=2)
print("args:", " ".join(a))
PYEOF'
echo
echo "=== 3) 重启 serve ==="
docker exec strata166 bash -lc 'pkill -f "serve/server.py" 2>/dev/null; pkill -f "build-906/strata" 2>/dev/null; sleep 3; ps aux | grep -E "[s]erver.py|[b]uild-906/strata" | head -3 || echo "  已清空"'
docker exec -d strata166 bash -lc 'cd /src && setsid nohup python3 serve/server.py --engine strata --config /data/strata-ud-q4_k_xl.json --port 8090 > /data/serve-run.log 2>&1 < /dev/null & echo started'
sleep 5
echo "--- 进程 ---"; docker exec strata166 bash -lc 'ps aux | grep -E "[s]erver.py|[b]uild-906/strata" | awk "{print \$3,\$4,\$11,\$12}" | head -3'
echo
for i in $(seq 1 20); do
  sleep 30
  echo "===== T+$((i*30))s ====="
  docker exec strata166 bash -lc 'tail -4 /data/serve-run.log; echo "  --- engine ---"; tail -4 /data/strata-ud-q4_k_xl.log; free -g | head -2 | tail -1'
  if docker exec strata166 bash -lc 'grep -q "ready: http" /data/serve-run.log 2>/dev/null'; then echo "### READY ###"; break; fi
  if ! docker exec strata166 bash -lc 'ps aux | grep -q "[s]erver.py"'; then echo "### 退出 ###"; break; fi
done
echo
echo "=== 最终 ==="
docker exec strata166 bash -lc 'tail -25 /data/serve-run.log; echo "=== engine 尾 12 ==="; tail -12 /data/strata-ud-q4_k_xl.log'
docker exec strata166 bash -lc 'curl -s -m 10 -o /dev/null -w "8090 http=%{http_code}\n" http://127.0.0.1:8090/v1/models'
'''

b64 = base64.b64encode(SCRIPT.encode('utf-8')).decode('ascii')
cmd = [SSH, '-o', 'BatchMode=yes', '-o', 'ConnectTimeout=10', '-o', 'ServerAliveInterval=30',
       '-i', KEY, HOST, 'base64 -d | bash']
r = subprocess.run(cmd, input=b64.encode('ascii'), capture_output=True, timeout=1800)
print(r.stdout.decode('utf-8', 'replace'))
if r.stderr.strip():
    print('ERR', r.stderr.decode('utf-8', 'replace')[:800])
