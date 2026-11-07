import subprocess, base64

SCRIPT = r'''
echo "=== containers ==="
docker ps -a --format "{{.Names}}|{{.Image}}|{{.Status}}" | grep -i strata | head -6
echo "=== health ==="
curl -s --max-time 10 http://127.0.0.1:8090/health
echo
echo "=== governor ==="
cat /sys/devices/system/cpu/cpu0/cpufreq/scaling_governor
echo "=== gpu ==="
/opt/rocm/bin/rocm-smi --showuse 2>/dev/null | grep -i "use" | head -2
'''


def run(script):
    p = subprocess.run(['ssh', '-o', 'BatchMode=yes', 'albus@192.168.50.166', 'base64 -d | bash'],
                       input=base64.b64encode(script.encode()), stdout=subprocess.PIPE,
                       stderr=subprocess.STDOUT, timeout=180)
    return p.stdout.decode('utf-8', 'replace')


print(run(SCRIPT))
