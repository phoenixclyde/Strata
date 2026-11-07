# -*- coding: utf-8 -*-
"""取 166 引擎日志（按臂切分：iq4_xs 的 prompt 计时行 + drafts accepted + 缓存命中）"""
import sys, re
sys.path.insert(0, r"D:/workbuddy/_z_rk80")
sys.stdout.reconfigure(encoding='utf-8')
import _sshutil

SCRIPT = r'''
set +e
F=/home/albus/strata166/data/strata-ud-iq4_xs.log
echo "=== 文件 ==="
ls -la $F
echo
echo "=== 全部 prompt 计时行（含 drafts）——最后 40 条 ==="
grep -E "prompt [0-9]+ tokens" $F | tail -40 | nl -ba
echo
echo "=== expert cache / resident RAM 最后 6 条 ==="
grep -E "decode expert cache hit rate|resident RAM" $F | tail -6
echo
echo "=== 各臂标志：'almost ready' / 启动行 ==="
grep -nE "strata serve: (starting|prompt 17|prompt 19)" $F | tail -12
echo
echo "=== 容器状态 ==="
docker ps --format '{{.Names}}|{{.Status}}|{{.Image}}' | grep -i strata
rocm-smi --showmeminfo vram 2>/dev/null | grep -i used
'''
rc, out, err = _sshutil.run_remote(SCRIPT, timeout=300, host="192.168.50.166")
print("rc =", rc)
print(out)
if err.strip():
    print("--- STDERR ---"); print(err[:1200])
