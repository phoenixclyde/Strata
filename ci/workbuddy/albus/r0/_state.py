import subprocess, base64

SCRIPT = r'''
echo "=== GPU ==="
/opt/rocm/bin/rocm-smi --showuse 2>/dev/null | grep -i "use" | head -2
echo "=== containers ==="
docker ps -a --format "{{.Names}}|{{.Image}}|{{.Status}}" | grep strata166 | head -6
echo "=== health ==="
curl -s --max-time 10 http://127.0.0.1:8090/health
echo
echo "=== metrics ==="
curl -s --max-time 10 http://127.0.0.1:8090/metrics | python3 -c "import sys,json;e=json.load(sys.stdin)['engine'];print('ver',e['version'],'slots',e['expert_slots'],'vram',e['vram_free_mib'])"
echo "=== governor ==="
cat /sys/devices/system/cpu/cpu*/cpufreq/scaling_governor | sort | uniq -c
echo "=== env ==="
python3 -c "import json;d=json.load(open('/home/albus/strata166/data/strata-huihui-ud-iq4_xs.json'));print('env',d.get('env'));print('args',len(d['args']))"
echo "=== helper scripts ==="
ls -l /home/albus/strata166/tmp/w776_bench.py /home/albus/strata166/tmp/w786_real.py 2>&1 | head -4
echo "=== config backups ==="
ls -t /home/albus/strata166/data/strata-huihui-ud-iq4_xs.json.bak_* 2>/dev/null | head -3
echo "=== mem ==="
grep -E "^(MemAvailable|SwapFree)" /proc/meminfo
'''


def run(script, timeout=240):
    p = subprocess.run(['ssh', '-o', 'BatchMode=yes', 'albus@192.168.50.166', 'base64 -d | bash'],
                       input=base64.b64encode(script.encode()), stdout=subprocess.PIPE,
                       stderr=subprocess.STDOUT, timeout=timeout)
    return p.stdout.decode('utf-8', 'replace')


print(run(SCRIPT))
