# W709 步11：取校准完整结果 + 服务复检
import sys, json
sys.path.insert(0, r'D:/workbuddy/_z_rk80')
import _sshutil

sc = r'''
D=/home/albus/strata166/w709
echo "=== run log 全文 ==="
cat $D/calib_run.log
echo
echo "=== calib_out.json 全文 ==="
cat $D/calib_out.json
echo
echo "=== 服务复检 ==="
docker ps --format '{{.Names}}|{{.Status}}' | grep -i strata
sleep 5
docker exec strata166-402 bash -lc 'curl -s -m 8 -o /dev/null -w "http=%{http_code}\n" http://127.0.0.1:8090/v1/models'
echo "=== 生产 config 有没有被动过 ==="
md5sum /home/albus/strata166/data/strata-ud-iq4_xs.json
echo "(批次A 终态应为 547d280c4c7c5d69f2440c9b8a16b975)"
echo "=== 生产日志有没有被校准污染 ==="
grep -c "strata-calib\|calib-learned" /data/strata-ud-iq4_xs.log 2>/dev/null || echo 0
echo "=== 校准专用 profile 有没有生成 ==="
ls -la /data/profiles/ 2>&1
'''
rc, out, err = _sshutil.run_remote(sc, timeout=400, host='192.168.50.166')
print('rc =', rc)
print(out)
if err.strip():
    print('--- STDERR ---'); print(err[:600])
# 落盘本地
try:
    j = out.split('=== calib_out.json 全文 ===')[1].split('=== 服务复检 ===')[0].strip()
    open(r'D:/workbuddy/_z_rk81/_w709_calib_out.json', 'w', encoding='utf-8', newline='').write(j)
    print('\n[local] saved _w709_calib_out.json  bytes =', len(j.encode()))
except Exception as e:
    print('[local] split failed:', e)
