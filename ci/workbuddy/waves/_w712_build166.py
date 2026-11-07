# 166 侧：后台启动 docker build（nohup，日志落盘），并立即回执
import subprocess, base64, time

OUT = r"D:/workbuddy_space/strata_ws/deploy/tmp/_w712_build166.out.txt"
f = open(OUT, "w", encoding="utf-8")
def log(s):
    line = "[%s] %s" % (time.strftime("%H:%M:%S"), s)
    print(line); f.write(line + "\n"); f.flush()

def run_remote(script, timeout=120):
    assert "\r" not in script
    b64 = base64.b64encode(script.encode("utf-8")).decode("ascii")
    p = subprocess.run(
        ["C:/Program Files/Git/usr/bin/ssh.exe", "-o", "BatchMode=yes", "-o", "ConnectTimeout=8",
         "albus@192.168.50.166", "base64 -d | bash"],
        input=(b64 + "\n").encode("ascii"), capture_output=True, timeout=timeout)
    return p.returncode, p.stdout.decode("utf-8", "replace"), p.stderr.decode("utf-8", "replace")

script = r"""
set -u
ctx=/home/albus/strata166/build-ctx-404
cd "$ctx"
if pgrep -f "docker build -t strata-gfx906:0.1.40.4" >/dev/null; then echo "BUILD_ALREADY_RUNNING"; exit 0; fi
setsid nohup docker build -f Dockerfile-0.1.40.4 -t strata-gfx906:0.1.40.4 . > "$ctx/build-404.log" 2>&1 < /dev/null &
sleep 5
echo "launched; pgrep:"; pgrep -af "docker build" | head -3
echo "log head:"; head -n 12 "$ctx/build-404.log" 2>/dev/null
"""
rc, out, err = run_remote(script, timeout=120)
log("build launch rc=%d" % rc)
f.write(out + "\n")
if err:
    f.write("STDERR:\n" + err + "\n")
f.close()
print(out)
