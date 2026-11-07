# W709 步1：摸 166 现状（只读）
import sys, time
sys.path.insert(0, r'D:/workbuddy/_z_rk80')
import _sshutil

sc = r'''
echo "=== T0 $(date -Is) ==="
echo "--- 容器 ---"
docker ps -a --format '{{.Names}}|{{.Status}}|{{.Image}}' | grep -i strata
echo "--- 服务健康 ---"
docker exec strata166-402 bash -lc 'curl -s -m 8 -o /dev/null -w "http=%{http_code}\n" http://127.0.0.1:8090/v1/models' 2>&1
echo "--- 现行 config md5 / 权限 ---"
ls -la /home/albus/strata166/data/strata-ud-iq4_xs.json
md5sum /home/albus/strata166/data/strata-ud-iq4_xs.json
echo "--- profiles ---"
ls -la /home/albus/strata166/data/profiles/ 2>&1
echo "--- VRAM ---"
rocm-smi --showmeminfo vram 2>/dev/null | grep -iE 'used|total' | head -4
echo "--- 当前启动块(最后一次 engine started 之后) ---"
L=/home/albus/strata166/data/strata-ud-iq4_xs.log
N=$(grep -n "engine started" $L | tail -1 | cut -d: -f1)
echo "engine_started_line=$N  total_lines=$(wc -l < $L)"
sed -n "${N}p" $L | cut -c1-1200
echo
echo "--- 校准工具是否在镜像里 ---"
docker exec strata166-402 bash -lc 'ls -la /src/tools/ 2>&1 | head -20; python3 -c "print(1)"' 2>&1
echo "--- 有没有曾在跑的 calibrate 进程 ---"
pgrep -af calibrate | head -5 || echo none
echo "--- 临时容器名占用 ---"
docker ps -a --format '{{.Names}}' | grep -iE 'calib|strata-tmp' || echo none
'''
rc, out, err = _sshutil.run_remote(sc, timeout=300, host='192.168.50.166')
print('rc =', rc)
print(out)
if err.strip():
    print('--- STDERR ---')
    print(err[:800])
