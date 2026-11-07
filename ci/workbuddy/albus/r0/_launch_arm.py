import subprocess, base64, hashlib, sys

local = r'D:/workbuddy_space/strata_ws/albus/r0/arm_run.sh'
name = sys.argv[1] if len(sys.argv) > 1 else 'arm'
pairs = sys.argv[2:]  # K V K V ...

data = open(local, 'rb').read()
b64 = base64.b64encode(data).decode('ascii')

launch = (
    "echo '%s' | base64 -d > /home/albus/strata166/tmp/arm_run.sh\n"
    "chmod +x /home/albus/strata166/tmp/arm_run.sh\n"
    "sh -n /home/albus/strata166/tmp/arm_run.sh && echo SYNTAX_OK\n"
    "cd /home/albus/strata166/tmp\n"
    "nohup sh arm_run.sh %s %s > arm_%s_launch.out 2>&1 < /dev/null &\n"
    "sleep 6; echo launched_%s\n"
) % (b64, name, ' '.join(pairs), name, name)

p = subprocess.run(['ssh', '-o', 'BatchMode=yes', 'albus@192.168.50.166', 'base64 -d | bash'],
                   input=base64.b64encode(launch.encode()), stdout=subprocess.PIPE,
                   stderr=subprocess.STDOUT, timeout=110)
print(p.stdout.decode('utf-8', 'replace'))
print('arm=%s overrides=%s local_md5=%s' % (name, pairs, hashlib.md5(data).hexdigest()[:8]))
