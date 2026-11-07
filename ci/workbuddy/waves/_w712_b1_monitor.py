# 本地监视：轮询 166 上的 b1.log，看到收尾标记即退出（用于触发后台完成通知）
import subprocess, base64, time, sys

SSH = 'C:/Program Files/Git/usr/bin/ssh.exe'
LOG = '/home/albus/strata166/w712/b1.log'


def sh(cmd, t=60):
    p = subprocess.run([SSH, '-o', 'BatchMode=yes', '-o', 'ConnectTimeout=8',
                        'albus@192.168.50.166', 'base64 -d | bash'],
                       input=base64.b64encode(cmd.encode()) + b'\n',
                       capture_output=True, timeout=t)
    return p.stdout.decode('utf-8', 'replace')


deadline = time.time() + 35 * 60
n = 0
while time.time() < deadline:
    n += 1
    try:
        out = sh('tail -n 2 /home/albus/strata166/w712/b1.log; echo "---"; pgrep -f b1_cacheevery.sh >/dev/null && echo RUNNING || echo NOTRUNNING')
    except Exception as e:
        out = 'ERR %r' % (e,)
    last = [x for x in out.splitlines() if x.strip()][:1]
    print('[%s poll%02d] %s' % (time.strftime('%H:%M:%S'), n, last[0] if last else ''), flush=True)
    if '=== W712 B1 done ===' in out:
        print('B1_DONE'); sys.exit(0)
    if 'NOTRUNNING' in out and n > 2:
        print('B1_PROCESS_GONE_WITHOUT_DONE_MARKER'); sys.exit(2)
    time.sleep(30)
print('B1_TIMEOUT'); sys.exit(3)
