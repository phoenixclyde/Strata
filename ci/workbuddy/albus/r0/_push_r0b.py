import subprocess, base64, hashlib

LOCAL = r'D:/workbuddy_space/strata_ws/albus/r0/r0b_gov.sh'
data = open(LOCAL, 'rb').read()
b64 = base64.b64encode(data).decode('ascii')

push = (
    "echo '%s' | base64 -d > /home/albus/strata166/tmp/r0b_gov.sh\n"
    "chmod +x /home/albus/strata166/tmp/r0b_gov.sh\n"
    "sh -n /home/albus/strata166/tmp/r0b_gov.sh && echo SYNTAX_OK\n"
    "md5sum /home/albus/strata166/tmp/r0b_gov.sh\n"
    "cd /home/albus/strata166/tmp && rm -f r0b_launch.out && nohup sh r0b_gov.sh > r0b_launch.out 2>&1 & \n"
    "sleep 10; echo launcher_started\n"
) % b64

p = subprocess.run(['ssh', '-o', 'BatchMode=yes', 'albus@192.168.50.166', 'base64 -d | bash'],
                   input=base64.b64encode(push.encode()), stdout=subprocess.PIPE,
                   stderr=subprocess.STDOUT, timeout=180)
print(p.stdout.decode('utf-8', 'replace'))
print('local md5', hashlib.md5(data).hexdigest())
