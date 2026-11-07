# 本地监视 B1b：看到收尾标记即退出（用于触发完成通知）
import subprocess, base64, time, sys

SSH = 'C:/Program Files/Git/usr/bin/ssh.exe'
MARK = '=== W712 B1b done ==='


def sh(cmd, t=60):
    p = subprocess.run([SSH, '-o', 'BatchMode=yes', '-o', 'ConnectTimeout=8',
                        'albus@192.168.50.166', 'base64 -d | bash'],
                       input=base64.b64encode(cmd.encode()) + b'\n',
                       capture_output=True, timeout=t)
    return p.stdout.decode('utf-8', 'replace')


deadline = time.time() + 40 * 60
n = 0
while time.time() < deadline:
    n += 1
    try:
        out = sh('tail -n 1 /home/albus/strata166/w712/b1b.log; echo "---"; '
                 'pgrep -f b1b_chunk.sh >/dev/null && echo RUNNING || echo NOTRUNNING')
    except Exception as e:
        out = 'ERR %r' % (e,)
    first = next((x for x in out.splitlines() if x.strip()), '')
    print('[%s poll%02d] %s' % (time.strftime('%H:%M:%S'), n, first), flush=True)
    if MARK in out:
        print('B1B_DONE'); sys.exit(0)
    if 'NOTRUNNING' in out and n > 2:
        print('B1B_PROCESS_GONE_WITHOUT_DONE_MARKER'); sys.exit(2)
    time.sleep(30)
print('B1B_TIMEOUT'); sys.exit(3)
