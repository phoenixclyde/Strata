import subprocess, base64, sys

SCRIPT = r'''
L=/home/albus/strata166/data/strata-huihui-ud-iq4_xs.log
echo "COUNT_7476="$(grep -a -c "74.76" $L)
echo "COUNT_7477="$(grep -a -c "74.7" $L)
echo "--- first 4 decode-timing lines ---"
grep -a "decode timing" $L | head -4
echo "--- last 4 decode-timing lines ---"
grep -a "decode timing" $L | tail -4
echo "--- total lines ---"
grep -a -c "decode timing" $L
'''


def run(script):
    p = subprocess.run(['ssh', '-o', 'BatchMode=yes', 'albus@192.168.50.166', 'base64 -d | bash'],
                       input=base64.b64encode(script.encode()), stdout=subprocess.PIPE, stderr=subprocess.STDOUT, timeout=240)
    return p.stdout.decode('utf-8', 'replace')


print(run(SCRIPT))
