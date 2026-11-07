import subprocess, base64
HOST = "albus@192.168.50.166"
SH = r'''
echo "===STARTUP==="
docker logs strata166-407 2>&1 | grep -E "pool workers|aux cpus|VRAM free with everything|expert cache auto|expert cache [0-9]+ slots|below 512|prefill chunk|resident RAM mode|prefill plan" | tail -10
echo "===WARN==="
docker logs strata166-407 2>&1 | grep -c "below 512 MiB" || true
echo "===METRICS==="
curl -s --max-time 5 http://127.0.0.1:8090/metrics | python3 -c "
import sys,json;d=json.load(sys.stdin);e=d['engine']
print('slots',e['expert_slots'],'vram_free',e['vram_free_mib'],'workers',e['pool_workers'])
"
'''
b64 = base64.b64encode(SH.encode()).decode("ascii")
p = subprocess.run(["ssh","-o","BatchMode=yes","-o","ConnectTimeout=10",HOST,"base64 -d | bash"],
                   input=b64.encode("ascii"), stdout=subprocess.PIPE, stderr=subprocess.PIPE)
print(p.stdout.decode("utf-8","replace")); print(p.stderr.decode("utf-8","replace")[:300])
