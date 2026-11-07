import subprocess, base64, re

SCRIPT = r'''
L=/home/albus/strata166/data/strata-huihui-ud-iq4_xs.log
echo "=== count: decode GPU stages ==="
grep -a -c "GPU stages" $L
echo "=== lines ==="
grep -a "GPU stages" $L | tail -8
echo "=== count 46.35 ==="
grep -a -c "46\.35" $L
echo "=== any line containing 46.3 ==="
grep -a "46\.3" $L | head -5
'''


def run(script):
    p = subprocess.run(['ssh', '-o', 'BatchMode=yes', 'albus@192.168.50.166', 'base64 -d | bash'],
                       input=base64.b64encode(script.encode()), stdout=subprocess.PIPE,
                       stderr=subprocess.STDOUT, timeout=240)
    return p.stdout.decode('utf-8', 'replace')


print(run(SCRIPT))
