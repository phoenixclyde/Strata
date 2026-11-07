# W709 步7：急处置——看门狗误把生产拉回，停掉它保住校准窗口
import sys
sys.path.insert(0, r'D:/workbuddy/_z_rk80')
import _sshutil

sc = r'''
set +e
D=/home/albus/strata166/w709
echo "=== 处置前：容器 ==="
docker ps --format '{{.Names}}|{{.Status}}' | grep -i -E 'strata'
echo "=== 处置前：KFD 进程 ==="
rocm-smi --showpids 2>/dev/null | sed -n '/KFD process/,$p' | head -12
echo "=== 处置前：VRAM ==="
rocm-smi --showmeminfo vram 2>/dev/null | grep -i used
echo
echo ">>> 停掉看门狗（已自行退出）与生产容器 <<<"
pkill -f 'w709/watchdog.sh' 2>/dev/null; echo "pkill watchdog rc=$?"
docker stop -t 30 strata166-402 >/dev/null 2>&1; echo "stop 402 rc=$?"
sleep 5
echo
echo "=== 处置后：容器 ==="
docker ps --format '{{.Names}}|{{.Status}}' | grep -i -E 'strata'
echo "=== 处置后：KFD 进程 ==="
rocm-smi --showpids 2>/dev/null | sed -n '/KFD process/,$p' | head -12
echo "=== 处置后：VRAM ==="
rocm-smi --showmeminfo vram 2>/dev/null | grep -i used
echo
echo "=== 校准进程还在吗 ==="
pgrep -af 'calibrate\.py|run_calib' | head -5
echo
echo "=== 校准 out 全文 ==="
cat $D/calib_out.json 2>/dev/null | tail -40
echo "out_bytes=$(stat -c %s $D/calib_out.json 2>/dev/null || echo 0)"
echo
echo "=== 校准 run log 尾 ==="
tail -6 $D/calib_run.log
echo
echo "=== 校准专用日志里 engine 有没有报错 ==="
grep -iE 'error|failed|out of memory|abort|ERR ' /data/strata-calib.log 2>/dev/null | tail -12
echo "calib_log_bytes=$(stat -c %s /data/strata-calib.log 2>/dev/null || echo 0)"
'''
rc, out, err = _sshutil.run_remote(sc, timeout=300, host='192.168.50.166')
print('rc =', rc)
print(out)
if err.strip():
    print('--- STDERR ---'); print(err[:600])
