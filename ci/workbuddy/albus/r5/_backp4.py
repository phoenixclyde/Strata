import subprocess, base64
def sh(s, t=300):
    p = subprocess.run(["ssh","-o","BatchMode=yes","-o","ConnectTimeout=10","albus@192.168.50.166","base64 -d | bash"],
                       input=base64.b64encode(s.encode()), stdout=subprocess.PIPE, stderr=subprocess.STDOUT, timeout=t)
    return p.stdout.decode("utf-8","replace")
print(sh(r'''
set -u
CONT=strata166-407
echo "before=$(docker inspect -f '{{.Config.Image}}' $CONT)"
docker rm -f "$CONT" >/dev/null 2>&1
docker rename "${CONT}.bak_w795" "$CONT" >/dev/null 2>&1 && echo RENAMED
docker start "$CONT" >/dev/null 2>&1
for i in $(seq 1 300); do curl -s --max-time 2 http://127.0.0.1:8090/health >/dev/null 2>&1 && { echo "ready ${i}s"; break; }; sleep 1; done
echo "after=$(docker inspect -f '{{.Config.Image}}' $CONT)"
curl -s --max-time 6 http://127.0.0.1:8090/metrics | python3 -c "import sys,json;e=json.load(sys.stdin)['engine'];print('slots',e['expert_slots'],'vram',e['vram_free_mib'],'ver',e['version'])"
python3 -c "import json;print(sorted(json.load(open('/home/albus/strata166/data/strata-huihui-ud-iq4_xs.json')).get('env',{}).items()))"
docker ps -a --format "{{.Names}}|{{.Image}}|{{.Status}}" | grep strata166 | head -4
''', t=300))
