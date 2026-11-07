import sys, time
sys.path.insert(0, "D:/workbuddy/_z_rk80")
import _sshutil

HOST = "192.168.50.166"

rc, out, err = _sshutil.run_remote(r'''
CTX=/home/albus/strata166/build-ctx-402
LOG=/home/albus/strata166/logs/build-402.log
mkdir -p /home/albus/strata166/logs
rm -f "$LOG"
cd "$CTX"
setsid nohup docker build -f Dockerfile-0.1.40.2 -t strata-gfx906:0.1.40.2 . > "$LOG" 2>&1 < /dev/null &
sleep 25
echo "--- pgrep build ---"
pgrep -af 'docker build' | head -3 || echo NO_BUILD_PROC
echo "--- docker 侧 ---"
docker ps --format '{{.Names}} | {{.Status}}' | head -8
echo "--- 日志头 40 行 ---"
head -40 "$LOG" 2>&1
echo "--- 日志尾 12 行 ---"
tail -12 "$LOG" 2>&1
''', timeout=300, host=HOST)
print("rc =", rc)
print(out)
if err.strip():
    print("--- STDERR ---")
    print(err[:1200])
