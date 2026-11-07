import subprocess, base64

LOCAL = r'D:/workbuddy_space/strata_ws/albus/r0/r0_run.sh'
data = open(LOCAL, 'rb').read()
b64 = base64.b64encode(data).decode('ascii')

script = (
    "mkdir -p /home/albus/strata166/tmp\n"
    "echo '%s' | base64 -d > /home/albus/strata166/tmp/r0_run.sh\n"
    "chmod +x /home/albus/strata166/tmp/r0_run.sh\n"
    "sh -n /home/albus/strata166/tmp/r0_run.sh && echo SYNTAX_OK\n"
    "md5sum /home/albus/strata166/tmp/r0_run.sh\n"
) % b64

p = subprocess.run(['ssh', '-o', 'BatchMode=yes', 'albus@192.168.50.166', 'base64 -d | bash'],
                   input=base64.b64encode(script.encode()), stdout=subprocess.PIPE,
                   stderr=subprocess.STDOUT, timeout=180)
print(p.stdout.decode('utf-8', 'replace'))
print('local md5', __import__('hashlib').md5(data).hexdigest())
