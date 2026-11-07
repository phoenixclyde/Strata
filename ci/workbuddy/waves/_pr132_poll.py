# W709 轮询校准进度
import sys
sys.path.insert(0, r'D:/workbuddy/_z_rk80')
import _sshutil

sc = r'''
D=/home/albus/strata166/w709
echo "=== $(date -Is) ==="
echo "--- 进程 ---"; pgrep -af 'w709/|calibrate\.py' | head -5
echo "--- 容器 ---"; docker ps --format '{{.Names}}|{{.Status}}' | grep -i strata || echo "(无)"
echo "--- out_bytes / mtime ---"; stat -c '%s  %y' $D/calib_out.json 2>/dev/null
echo "--- out 尾部 ---"; tail -22 $D/calib_out.json 2>/dev/null
echo "--- run log 尾 ---"; tail -3 $D/calib_run.log
echo "--- watchdog2 ---"; tail -2 $D/watchdog2.log 2>/dev/null
'''
rc, out, err = _sshutil.run_remote(sc, timeout=200, host='192.168.50.166')
print('rc =', rc)
print(out)
if err.strip():
    print('--- STDERR ---'); print(err[:400])
