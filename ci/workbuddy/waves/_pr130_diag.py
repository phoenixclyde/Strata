# W709 步9：判活——校准引擎是在慢还是卡住
import sys, time
sys.path.insert(0, r'D:/workbuddy/_z_rk80')
import _sshutil

sc = r'''
D=/home/albus/strata166/w709
P=$(pgrep -f 'build-906/strata' | head -1)
echo "engine pid = $P"
echo "=== /proc/$P 状态（可两次采样看是否在推进）==="
for k in 1 2; do
  if [ -n "$P" ] && [ -d /proc/$P ]; then
    echo "--- sample $k $(date +%T) ---"
    awk '{print "utime="$14" stime="$15}' /proc/$P/stat
    grep -E 'State|VmRSS|Threads' /proc/$P/status
  fi
  sleep 6
done
echo
echo "=== 校准引擎的 cmdline ==="
if [ -n "$P" ]; then tr '\0' ' ' < /proc/$P/cmdline; echo; fi
echo
echo "=== 容器内进程树 ==="
docker exec strata-calib bash -lc 'ps -eo pid,ppid,stat,etime,pcpu,rss,args | head -20'
echo
echo "=== 容器内 RAM/加载进度 ==="
docker exec strata-calib bash -lc 'free -g | head -2; grep -E "MemAvailable|Cached" /proc/meminfo'
echo
echo "=== 校准 out 现在多大 ==="
stat -c '%s %y' $D/calib_out.json
tail -6 $D/calib_out.json
echo
echo "=== calib 专用日志 ==="
ls -la /data/strata-calib.log 2>&1
tail -20 /data/strata-calib.log 2>/dev/null
echo
echo "=== setup.py / server.py 里那句 still starting 出自哪 ==="
docker exec strata-calib bash -lc 'grep -rn "still starting" /src/*.py /src/serve/*.py 2>/dev/null | head -5'
echo
echo "=== dmesg 有无 OOM / GPU 复位 ==="
dmesg 2>/dev/null | tail -12 || sudo -n dmesg 2>/dev/null | tail -12 || echo "(no dmesg)"
'''
rc, out, err = _sshutil.run_remote(sc, timeout=300, host='192.168.50.166')
print('rc =', rc)
print(out)
if err.strip():
    print('--- STDERR ---'); print(err[:600])
