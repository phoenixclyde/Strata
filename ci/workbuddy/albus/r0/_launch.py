import subprocess, base64, sys

script = r'''
cd /home/albus/strata166/tmp
rm -f r0_launch.out
nohup sh r0_run.sh > r0_launch.out 2>&1 &
echo "pid=$!"
sleep 8
ls -t /home/albus/strata166/data/r0_results_*.txt 2>/dev/null | head -1
cat $(ls -t /home/albus/strata166/data/r0_results_*.txt 2>/dev/null | head -1) 2>/dev/null | head -20
'''

p = subprocess.run(['ssh', '-o', 'BatchMode=yes', 'albus@192.168.50.166', 'base64 -d | bash'],
                   input=base64.b64encode(script.encode()), stdout=subprocess.PIPE,
                   stderr=subprocess.STDOUT, timeout=180)
print(p.stdout.decode('utf-8', 'replace'))
