# 监视 B3 收尾
import base64, subprocess, sys, time

MARK = '=== W713 B3 收尾完毕 ==='


def sh(cmd, t=60):
    p = subprocess.run(["C:/Program Files/Git/usr/bin/ssh.exe", "-o", "BatchMode=yes",
                        "-o", "ConnectTimeout=8", "albus@192.168.50.166", "base64 -d | bash"],
                       input=base64.b64encode(cmd.encode()) + b"\n", capture_output=True, timeout=t)
    return p.stdout.decode("utf-8", "replace")


deadline = time.time() + 40 * 60
n = 0
while time.time() < deadline:
    n += 1
    try:
        out = sh('tail -n 1 /home/albus/strata166/w712/b3.log; echo "---"; '
                 'pgrep -f b3_convcache.sh >/dev/null && echo RUNNING || echo NOTRUNNING')
    except Exception as e:
        out = "ERR %r" % (e,)
    first = next((x for x in out.splitlines() if x.strip()), "")
    print("[%s #%02d] %s" % (time.strftime("%H:%M:%S"), n, first[:150]), flush=True)
    if MARK in out:
        print("B3_DONE"); sys.exit(0)
    if "NOTRUNNING" in out and n > 2:
        print("B3_GONE_WITHOUT_MARKER"); sys.exit(2)
    time.sleep(30)
print("B3_TIMEOUT"); sys.exit(3)
