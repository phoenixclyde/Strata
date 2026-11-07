# -*- coding: utf-8 -*-
"""回滚：推干净 config + 把生产从 0.2.4r5 切回 0.2.4（bak024 容器）。"""
import base64, hashlib, subprocess, sys

HOST = "albus@192.168.50.166"
LOCAL = r"D:/workbuddy_space/strata_ws/deploy/params/generated/strata-huihui-ud-iq4_xs.json"
REMOTE = "/home/albus/strata166/data/strata-huihui-ud-iq4_xs.json"

def run(script, timeout=900):
    p = subprocess.run(["ssh", "-o", "BatchMode=yes", HOST, "base64 -d | bash"],
                       input=base64.b64encode(script.encode()),
                       stdout=subprocess.PIPE, stderr=subprocess.STDOUT, timeout=timeout)
    return p.stdout.decode("utf-8", "replace")

data = open(LOCAL, "rb").read()
want = hashlib.md5(data).hexdigest()
b = base64.b64encode(data).decode("ascii")
o = run("echo '%s' | base64 -d > %s.tmp && mv %s.tmp %s && md5sum %s" % (b, REMOTE, REMOTE, REMOTE, REMOTE))
print("[push config] want=%s  %s" % (want[:12], "OK" if want in o else "MISMATCH"))
if want not in o:
    print(o[-400:]); sys.exit(2)

SH = r'''
set -u
CUR=strata166-407
BAK=strata166-407.bak024
ASIDE=strata166-407.r5
echo "=== stop r5 ==="; docker stop $CUR >/dev/null 2>&1; echo rc=$?
echo "=== rename r5 aside ==="; docker rename $CUR $ASIDE 2>&1; echo rc=$?
echo "=== restore bak024 ==="; docker rename $BAK $CUR 2>&1; echo rc=$?
docker start $CUR >/dev/null 2>&1; echo "start rc=$?"
for i in $(seq 1 120); do
  if curl -s --max-time 2 http://127.0.0.1:8090/health >/dev/null 2>&1; then echo "READY ${i}s"; break; fi
  sleep 1
done
'''
print(run(SH)[-900:])

VER = r'''
echo "=== container ==="
docker ps --format "{{.Names}}|{{.Image}}|{{.Status}}" | grep strata166
echo "=== health ==="
curl -s --max-time 10 http://127.0.0.1:8090/health
echo
echo "=== engine ==="
curl -s --max-time 10 http://127.0.0.1:8090/metrics | python3 -c "import sys,json;e=json.load(sys.stdin)['engine'];print('ver',e['version'],'slots',e['expert_slots'],'vram',e['vram_free_mib'])"
echo "=== live env ==="
python3 -c "import json;d=json.load(open('/home/albus/strata166/data/strata-huihui-ud-iq4_xs.json'));print(d.get('env'));print('resident', '--resident-experts' in d.get('args',[]))"
echo "=== governor ==="
cat /sys/devices/system/cpu/cpu*/cpufreq/scaling_governor | sort | uniq -c
echo "=== mem ==="
grep -E "^(MemAvailable|SwapFree)" /proc/meminfo
'''
print(run(VER)[-1800:])
