# W709 步12：只读核查（临时容器清理 / profiles / 现场）
import sys
sys.path.insert(0, r'D:/workbuddy/_z_rk80')
import _sshutil

sc = r'''
D=/home/albus/strata166/w709
echo "=== 临时容器是否清干净 ==="
docker ps -a --format '{{.Names}}|{{.Status}}' | grep -E 'strata' || echo "(none)"
echo
echo "=== profiles 目录（宿主真实路径）==="
ls -la /home/albus/strata166/data/profiles/
echo
echo "=== 校准留下的文件 ==="
ls -la $D/
echo
echo "=== 生产 config 现行 ==="
md5sum /home/albus/strata166/data/strata-ud-iq4_xs.json
cat /home/albus/strata166/data/strata-ud-iq4_xs.json | python3 -c "import json,sys; d=json.load(sys.stdin); print('args tail:', ' '.join(d['args'][-6:])); print('env:', d.get('env'))"
echo
echo "=== A/B 进度（本地驱动写的 cfg_A/cfg_B + bench）==="
ls -la $D/cfg_A.json $D/cfg_B.json 2>&1
grep -o 'R2.2\|resident RAM mode[^,]*' /data/strata-ud-iq4_xs.log 2>/dev/null | tail -2
echo "engine_started_tail:"
grep "engine started" /data/strata-ud-iq4_xs.log | tail -1 | grep -o -- '--pcie-frac [0-9.]*\|--spec-min-p [0-9.]*' || echo "(无校准旋钮)"
'''
rc, out, err = _sshutil.run_remote(sc, timeout=200, host='192.168.50.166')
print(out)
if err.strip():
    print('--- STDERR ---'); print(err[:400])
