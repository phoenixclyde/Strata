import subprocess, base64

SCRIPT = r'''
/opt/rocm/bin/rocminfo 2>/dev/null | grep -n "Compute Unit" | head -6
echo "=== rocm-smi ==="
/opt/rocm/bin/rocm-smi --showhw 2>/dev/null | head -12
echo "=== wavefront / LDS ==="
/opt/rocm/bin/rocminfo 2>/dev/null | grep -i -E "wavefront|Local Memory|Max Work" | head -6
'''


def run(script):
    p = subprocess.run(['ssh', '-o', 'BatchMode=yes', 'albus@192.168.50.166', 'base64 -d | bash'],
                       input=base64.b64encode(script.encode()), stdout=subprocess.PIPE,
                       stderr=subprocess.STDOUT, timeout=240)
    return p.stdout.decode('utf-8', 'replace')


print(run(SCRIPT))
