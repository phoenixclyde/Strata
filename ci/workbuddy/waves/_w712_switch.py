# 执行切换：停 -402 / 起 -404（脚本内含 300 s 轮询 + 自动回滚）
import subprocess, base64, time

OUT = r"D:/workbuddy_space/strata_ws/deploy/tmp/_w712_switch.out.txt"
f = open(OUT, "w", encoding="utf-8")
def log(s):
    line = "[%s] %s" % (time.strftime("%H:%M:%S"), s)
    print(line); f.write(line + "\n"); f.flush()

script = r"""
set -u
/home/albus/strata166/w712/switch_404.sh
echo "SWITCH_RC=$?"
"""
b64 = base64.b64encode(script.encode("utf-8")).decode("ascii")
t0 = time.time()
p = subprocess.run(
    ["C:/Program Files/Git/usr/bin/ssh.exe", "-o", "BatchMode=yes", "-o", "ConnectTimeout=8",
     "-o", "ServerAliveInterval=15", "albus@192.168.50.166", "base64 -d | bash"],
    input=(b64 + "\n").encode("ascii"), capture_output=True, timeout=540)
log("switch ssh rc=%d in %.1fs" % (p.returncode, time.time() - t0))
f.write(p.stdout.decode("utf-8", "replace") + "\n")
if p.stderr.strip():
    f.write("STDERR:\n" + p.stderr.decode("utf-8", "replace") + "\n")
f.close()
print(p.stdout.decode("utf-8", "replace"))
print("STDERR:", p.stderr.decode("utf-8", "replace")[-300:])
