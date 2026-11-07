# W709 步3：校准窗口的前置检查（只读，fail-closed）
import sys
sys.path.insert(0, r'D:/workbuddy/_z_rk80')
import _sshutil

sc = r'''
echo "=== A) tokenizer 三件 ==="
docker exec strata166-402 bash -lc 'ls -la /data/packs/ud-iq4_xs/tokenizer/ 2>&1 | head -12'
echo "--- 逐个判 ---"
docker exec strata166-402 bash -lc 'for f in vocab.json merges.txt token_type.json; do printf "  %-18s " $f; [ -f /data/packs/ud-iq4_xs/tokenizer/$f ] && echo YES || echo NO; done'
echo
echo "=== B) calibrate 能不能 import（无参应打 usage）==="
docker exec strata166-402 bash -lc 'cd /src && python3 tools/calibrate.py 2>&1 | tail -6'
echo "B_RC=$?"
echo
echo "=== C) 磁盘与 python ==="
df -h / | tail -1
docker exec strata166-402 python3 -V
echo
echo "=== D) 引擎 --help 里这 6 个旋钮的原文 ==="
docker exec strata166-402 bash -lc '/src/build-906/strata --help 2>&1' | grep -A3 -E '^\s+--(pcie-frac|spec-min-p|pool-workers|adapt-every|adapt-swaps|adapt-decay)\b' | head -40
echo
echo "=== E) 现有 engine started 行（校准要照它起步）==="
grep "engine started" /home/albus/strata166/data/strata-ud-iq4_xs.log | tail -1 | cut -c1-700
'''
rc, out, err = _sshutil.run_remote(sc, timeout=300, host='192.168.50.166')
print('rc =', rc)
print(out)
if err.strip():
    print('--- STDERR ---')
    print(err[:600])
