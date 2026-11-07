import subprocess, base64

SCRIPT = r'''
echo "=== containers ==="
docker ps -a --format "{{.Names}}|{{.Image}}|{{.Status}}" | grep strata166 | head -8
echo "=== health ==="
curl -s --max-time 10 http://127.0.0.1:8090/health
echo
echo "=== metrics ==="
curl -s --max-time 10 http://127.0.0.1:8090/metrics | python3 -c "import sys,json;e=json.load(sys.stdin)['engine'];print('ver',e['version'],'slots',e['expert_slots'],'vram',e['vram_free_mib'])" 2>&1
echo "=== governor ==="
cat /sys/devices/system/cpu/cpu*/cpufreq/scaling_governor 2>/dev/null | sort | uniq -c
echo "=== env ==="
python3 -c "import json;d=json.load(open('/home/albus/strata166/data/strata-huihui-ud-iq4_xs.json'));print('env',d.get('env'))" 2>&1
echo "=== tmp scripts ==="
ls -l /home/albus/strata166/tmp/*.py 2>/dev/null | tail -12
echo "=== load ==="
cat /proc/loadavg
echo "=== gpu ==="
/opt/rocm/bin/rocm-smi --showuse 2>/dev/null | grep -i "gpu use" | head -3
'''

def run(script, timeout=240):
    p = subprocess.run(['ssh', '-o', 'BatchMode=yes', 'albus@192.168.50.166', 'base64 -d | bash'],
                       input=base64.b64encode(script.encode()), stdout=subprocess.PIPE,
                       stderr=subprocess.STDOUT, timeout=timeout)
    return p.stdout.decode('utf-8', 'replace')

print(run(SCRIPT))
