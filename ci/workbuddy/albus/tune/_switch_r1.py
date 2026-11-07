import subprocess, base64, sys

HOST = "albus@192.168.50.166"

SH = r'''
set -u
OLD=strata166-407
BAK=strata166-407.bak024
IMG=strata-gfx906:0.2.4r1

echo "=== step1 stop old ==="
docker stop $OLD >/dev/null 2>&1; echo "stopped rc=$?"

echo "=== step2 rename ==="
docker rename $OLD $BAK 2>&1; echo "renamed rc=$?"

echo "=== step3 run new ==="
docker run -d --name $OLD \
  --device=/dev/kfd --device=/dev/dri --group-add video \
  --ipc=host --ulimit memlock=-1 --shm-size=64m \
  --security-opt label=disable \
  -p 8090:8090 \
  -v /home/albus/strata166/data:/data \
  -v /models:/models:ro \
  --restart unless-stopped \
  -w /src \
  $IMG /bin/bash -lc "cd /src && exec python3 serve/server.py --engine strata --config /data/strata-huihui-ud-iq4_xs.json --port 8090" >/dev/null 2>&1
echo "run rc=$?"

echo "=== step4 wait ready ==="
OK=0
for i in $(seq 1 50); do
  H=$(curl -s --max-time 4 http://127.0.0.1:8090/health 2>/dev/null)
  case "$H" in *'"loaded": true'*) echo "ready after ~$((i*3))s"; OK=1; break;; esac
  sleep 3
done

if [ "$OK" != "1" ]; then
  echo "!!! NOT READY -> rollback"
  docker stop $OLD >/dev/null 2>&1; docker rm $OLD >/dev/null 2>&1
  docker rename $BAK $OLD
  docker start $OLD >/dev/null 2>&1
  echo "rolled back to 0.2.3"
  exit 1
fi

echo "=== metrics ==="
curl -s --max-time 5 http://127.0.0.1:8090/metrics | python3 -c "
import sys,json
d=json.load(sys.stdin); e=d['engine']; hw=d['hardware']; st=d['hardware_static']
print('version',e['version'],'| kv',e['kv'],'| slots',e['expert_slots'],'| cache_mib',e['expert_cache_mib'])
print('vram_free',e['vram_free_mib'],'| workers',e['pool_workers'],'| prefill_cap',e['prefill_cap'],'| context',e['context'])
print('gpu_name',st.get('gpu_name'),'| pcie gen',hw.get('gpu_pcie_gen'),'width',hw.get('gpu_pcie_width'),'| rx',hw.get('gpu_pcie_rx_mb'))
print('spec',e['spec'],'mtp_max',e['mtp_max'],'lookup',e['lookup'],'arena',e['arena_mib'])
"
echo "=== startup ==="
L=/home/albus/strata166/data/strata-huihui-ud-iq4_xs.log
n=$(grep -n "engine started" $L | tail -1 | cut -d: -f1)
tail -n +$n $L | grep -E "pool workers|VRAM free with everything|expert cache [0-9]+ slots|prefill chunk|resident RAM mode|below 512" | head -6
'''

p = subprocess.run(["ssh", "-o", "BatchMode=yes", "-o", "ServerAliveInterval=15", HOST, "base64 -d | bash"],
                   input=base64.b64encode(SH.encode()).decode("ascii").encode("ascii"),
                   stdout=subprocess.PIPE, stderr=subprocess.STDOUT, timeout=400)
print(p.stdout.decode("utf-8", "replace"))
