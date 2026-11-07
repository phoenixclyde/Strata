# W709 步6：看现成 bench 件 + 校准进度
import sys
sys.path.insert(0, r'D:/workbuddy/_z_rk80')
import _sshutil

sc = r'''
D=/home/albus/strata166/w709
echo "=== bench_ver.py（生产机上的现成件）==="
ls -la /home/albus/strata166/data/bench_ver.py 2>&1
echo ---
sed -n '1,120p' /home/albus/strata166/data/bench_ver.py 2>/dev/null
echo
echo "=== 校准进度：run log ==="
cat $D/calib_run.log
echo
echo "=== 校准进度：out 尾部 ==="
tail -30 $D/calib_out.json 2>/dev/null
echo "out_bytes=$(stat -c %s $D/calib_out.json 2>/dev/null || echo 0)"
echo
echo "=== 看门狗 ==="
cat $D/watchdog.log 2>/dev/null
'''
rc, out, err = _sshutil.run_remote(sc, timeout=200, host='192.168.50.166')
print('rc =', rc)
print(out)
if err.strip():
    print('--- STDERR ---'); print(err[:500])
