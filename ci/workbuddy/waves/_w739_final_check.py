# W709 步24：终态核查 + register 同步 166
import sys, hashlib, os
sys.path.insert(0, r'D:/workbuddy/_z_rk80')
import _sshutil

# 同步 register + 核验器 + 生成器到 166（保证"唯一真值"两机一致）
for lp, rp in [(r'D:/strata166/params/PARAM_REGISTER.tsv', '/home/albus/strata166/params/PARAM_REGISTER.tsv'),
               (r'D:/strata166/params/gen_config.py', '/home/albus/strata166/params/gen_config.py'),
               (r'D:/strata166/params/verify_config.py', '/home/albus/strata166/params/verify_config.py'),
               (r'D:/strata166/W709_PARAM_OPTIMUM.md', '/home/albus/strata166/W709_PARAM_OPTIMUM.md')]:
    ok, size, md5, det = _sshutil.push_b64(lp, rp)
    print('push %-44s ok=%s size=%s md5=%s' % (rp.split('/')[-1], ok, size, md5))

sc = r'''
D=/home/albus/strata166/w709
echo "=== 容器 ==="
docker ps -a --format '{{.Names}}|{{.Status}}|{{.Image}}' | grep -i strata
echo "=== 服务 ==="
docker exec strata166-402 bash -lc 'curl -s -m 8 -o /dev/null -w "http=%{http_code}\n" http://127.0.0.1:8090/v1/models'
echo "=== LIVE config md5（应 d2b10f0c4e8293ba010614c7acc70bea）==="
md5sum /home/albus/strata166/data/strata-ud-iq4_xs.json
echo "=== 最后一次 engine started 的关键旋钮 ==="
grep "engine started" /home/albus/strata166/data/strata-ud-iq4_xs.log | tail -1 | grep -o -- '--pcie-frac [0-9.]*\|--spec-min-p [0-9.]*\|--prompt-cache-every [0-9]*'
echo "=== 残留进程 / 临时容器 ==="
pgrep -af '_w680|_mkpr|calibrate|run_calib' | head -5 || echo "(无残留)"
docker ps -a --format '{{.Names}}' | grep -E 'calib|strata-calib' || echo "(无临时容器)"
echo "=== 磁盘 / VRAM ==="
df -h / | tail -1
rocm-smi --showmeminfo vram 2>/dev/null | grep -i used
echo "=== register 行数与状态 ==="
python3 -c "
import io, collections
L=io.open('/home/albus/strata166/params/PARAM_REGISTER.tsv',encoding='utf-8').read().splitlines()
print(' 行数(不含表头) =', len(L)-1)
print(' status =', dict(collections.Counter(x.split(chr(9))[5] for x in L[1:] if x.strip())))
"
'''
rc, out, err = _sshutil.run_remote(sc, timeout=300, host='192.168.50.166')
print()
print(out)
if err.strip():
    print('--- STDERR ---'); print(err[:400])
