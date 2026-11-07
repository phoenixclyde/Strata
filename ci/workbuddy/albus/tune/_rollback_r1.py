import subprocess, base64

HOST = "albus@192.168.50.166"
SH = r'''
set -u
CUR=strata166-407
BAK=strata166-407.bak024
R1=strata166-407.r1

echo "=== 1 stop r1 container ==="
docker stop $CUR >/dev/null 2>&1; echo "stopped rc=$?"

echo "=== 2 rename r1 aside ==="
docker rename $CUR $R1 2>&1; echo "renamed rc=$?"

echo "=== 3 restore 0.2.4 container ==="
docker rename $BAK $CUR 2>&1; echo "restored rc=$?"
docker start $CUR >/dev/null 2>&1; echo "start rc=$?"

echo "=== 4 wait ready ==="
for i in $(seq 1 60); do
  if curl -s --max-time 2 http://127.0.0.1:8090/health >/dev/null 2>&1; then echo "ready after ~${i}s"; break; fi
  sleep 1
done

echo "=== 5 verify ==="
docker ps --format '{{.Names}}|{{.Image}}|{{.Status}}' | grep strata166 | head -3
curl -s --max-time 8 http://127.0.0.1:8090/metrics | python3 -c "
import sys,json
d=json.load(sys.stdin)
e=d['engine']
print('ver',e['version'],'slots',e['expert_slots'],'vram',e['vram_free_mib'])
"
echo -n "image inside container: "; docker inspect $CUR --format '{{.Config.Image}}'
'''

p = subprocess.run(["ssh", "-o", "BatchMode=yes", HOST, "base64 -d | bash"],
                   input=base64.b64encode(SH.encode()),
                   stdout=subprocess.PIPE, stderr=subprocess.STDOUT, timeout=600)
print(p.stdout.decode("utf-8", "replace"))
