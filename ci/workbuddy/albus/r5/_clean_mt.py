import subprocess, base64
def sh(s, t=600):
    p = subprocess.run(["ssh","-o","BatchMode=yes","-o","ConnectTimeout=10","albus@192.168.50.166","base64 -d | bash"],
                       input=base64.b64encode(s.encode()), stdout=subprocess.PIPE, stderr=subprocess.STDOUT, timeout=t)
    return p.stdout.decode("utf-8","replace")
print(sh(r'''python3 - <<'PY'
import json
p='/home/albus/strata166/data/strata-huihui-ud-iq4_xs.json'
d=json.load(open(p)); d.get('env',{}).pop('STRATA_PREFILL_TIMING',None)
json.dump(d, open(p,'w'), indent=2, ensure_ascii=False); print('timing off env_n=%d'%len(d.get('env',{})))
PY
docker restart strata166-407 >/dev/null 2>&1
for i in $(seq 1 300); do curl -s --max-time 2 http://127.0.0.1:8090/health >/dev/null 2>&1 && { echo ready=${i}s; break; }; sleep 1; done
L=/home/albus/strata166/data/strata-huihui-ud-iq4_xs.log
prev=$(grep -ac "conversation cache:" "$L")
cd /home/albus/strata166/tmp && python3 mt_floor.py 2>&1 | head -12
now=$(grep -ac "conversation cache:" "$L")
echo "=== new park lines: $((now-prev)) ==="
grep -a "conversation cache:" "$L" | tail -n +$((prev+1)) | cut -c1-190''', t=560))
