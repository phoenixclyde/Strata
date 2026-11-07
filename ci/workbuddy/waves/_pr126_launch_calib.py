# W709 步5：推两个窗口脚本 + 语法检查 + 起窗口（+看门狗）
import sys
sys.path.insert(0, r'D:/workbuddy/_z_rk80')
import _sshutil

FILES = [
    (r'D:/workbuddy/_z_rk81/remote/w709_run_calib.sh', '/home/albus/strata166/w709/run_calib.sh'),
    (r'D:/workbuddy/_z_rk81/remote/w709_watchdog.sh', '/home/albus/strata166/w709/watchdog.sh'),
]
for lp, rp in FILES:
    b = open(lp, 'rb').read()
    assert b.count(b'\r') == 0, 'CRLF in %s' % lp
    assert not b.startswith(b'\xef\xbb\xbf'), 'BOM in %s' % lp
    ok, size, md5, det = _sshutil.push_b64(lp, rp)
    print('push %-46s ok=%s size=%s md5=%s' % (rp.split('/')[-1], ok, size, md5))

CHK = r'''
set -u
D=/home/albus/strata166/w709
chmod +x $D/run_calib.sh $D/watchdog.sh
echo "=== bash -n 语法检查 ==="
bash -n $D/run_calib.sh && echo "run_calib.sh OK" || echo "run_calib.sh SYNTAX_FAIL"
bash -n $D/watchdog.sh && echo "watchdog.sh OK" || echo "watchdog.sh SYNTAX_FAIL"
echo "=== 文件指纹 ==="
md5sum $D/run_calib.sh $D/watchdog.sh
echo "=== 当前容器/GPU ==="
docker ps --format '{{.Names}}|{{.Status}}' | grep -i strata
rocm-smi --showmeminfo vram 2>/dev/null | grep -i used
'''
rc, out, err = _sshutil.run_remote(CHK, timeout=200, host='192.168.50.166')
print(out)
if err.strip():
    print('--- STDERR ---'); print(err[:500])

LAUNCH = r'''
set -u
D=/home/albus/strata166/w709
rm -f $D/run_calib.out $D/watchdog.out
cd $D
( setsid nohup bash $D/watchdog.sh > $D/watchdog.out 2>&1 < /dev/null & )
sleep 2
( setsid nohup bash $D/run_calib.sh > $D/run_calib.out 2>&1 < /dev/null & )
sleep 25
echo "=== pgrep ==="
pgrep -af 'run_calib|watchdog' | head -5
echo "=== run log ==="
cat $D/calib_run.log 2>/dev/null
echo "=== 容器 ==="
docker ps --format '{{.Names}}|{{.Status}}' | grep -i -E 'strata'
echo "=== VRAM ==="
rocm-smi --showmeminfo vram 2>/dev/null | grep -i used
'''
rc, out, err = _sshutil.run_remote(LAUNCH, timeout=400, host='192.168.50.166')
print('launch rc =', rc)
print(out)
if err.strip():
    print('--- STDERR ---'); print(err[:600])
