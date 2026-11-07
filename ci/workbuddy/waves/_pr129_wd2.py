# W709 步8：推修正版看门狗并启动；同时看校准进度
import sys
sys.path.insert(0, r'D:/workbuddy/_z_rk80')
import _sshutil

lp = r'D:/workbuddy/_z_rk81/remote/w709_watchdog2.sh'
b = open(lp, 'rb').read()
assert b.count(b'\r') == 0 and not b.startswith(b'\xef\xbb\xbf')
ok, size, md5, det = _sshutil.push_b64(lp, '/home/albus/strata166/w709/watchdog2.sh')
print('push watchdog2 ok=%s size=%s md5=%s' % (ok, size, md5))

sc = r'''
set -u
D=/home/albus/strata166/w709
chmod +x $D/watchdog2.sh
bash -n $D/watchdog2.sh && echo "watchdog2 syntax OK"
pkill -f 'w709/watchdog2.sh' 2>/dev/null || true
( setsid nohup bash $D/watchdog2.sh > $D/watchdog2.out 2>&1 < /dev/null & )
sleep 3
echo "=== pgrep ==="
pgrep -af 'w709/' | head -6
echo
echo "=== 容器 ==="
docker ps --format '{{.Names}}|{{.Status}}' | grep -i strata
echo "=== KFD ==="
rocm-smi --showpids 2>/dev/null | sed -n '/KFD process/,$p' | head -8
echo
echo "=== 校准 out 尾部 ==="
tail -25 $D/calib_out.json 2>/dev/null
echo "out_bytes=$(stat -c %s $D/calib_out.json 2>/dev/null || echo 0)"
echo "calib_log_bytes=$(stat -c %s /data/strata-calib.log 2>/dev/null || echo 0)"
echo
echo "=== 校准专用日志尾 ==="
tail -8 /data/strata-calib.log 2>/dev/null
'''
rc, out, err = _sshutil.run_remote(sc, timeout=300, host='192.168.50.166')
print('rc =', rc)
print(out)
if err.strip():
    print('--- STDERR ---'); print(err[:600])
