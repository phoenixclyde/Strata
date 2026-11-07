# 轮询 166 上的构建日志（只读）
import subprocess, base64, sys, time

def run_remote(script, timeout=120):
    assert "\r" not in script
    b64 = base64.b64encode(script.encode("utf-8")).decode("ascii")
    p = subprocess.run(
        ["C:/Program Files/Git/usr/bin/ssh.exe", "-o", "BatchMode=yes", "-o", "ConnectTimeout=8",
         "albus@192.168.50.166", "base64 -d | bash"],
        input=(b64 + "\n").encode("ascii"), capture_output=True, timeout=timeout)
    return p.returncode, p.stdout.decode("utf-8", "replace"), p.stderr.decode("utf-8", "replace")

tail = int(sys.argv[1]) if len(sys.argv) > 1 else 25
script = r"""
set -u
ctx=/home/albus/strata166/build-ctx-404
echo "== build proc =="
pgrep -af "docker build" | head -3 || echo "(no docker build proc)"
echo "== log tail =="
tail -n %d "$ctx/build-404.log" 2>/dev/null || echo "(no log)"
echo "== images strata =="
docker images --format '{{.Repository}}:{{.Tag}} | {{.Size}} | {{.CreatedAt}}' | grep -i strata
""" % tail
rc, out, err = run_remote(script)
print(out)
if err.strip():
    print("STDERR:", err[:300])
