# -*- coding: utf-8 -*-
"""166：查证 MMQ 是否真的在用（构建期宏 + 运行期日志 + 二进制符号）"""
import base64, os, subprocess

KEY = os.path.expanduser('~/.ssh/id_ed25519_workbuddy')
SSH = r'C:\Program Files\Git\usr\bin\ssh.exe'
HOST = 'albus@192.168.50.166'

SC = r'''
echo "=== A) 构建期：CMakeCache 里的 STRATA_* 关键项 ==="
docker exec strata166 bash -lc 'for f in /src/build-906/CMakeCache.txt /src/build-hip/CMakeCache.txt; do [ -f "$f" ] || continue; echo "--- $f ---"; grep -E "^STRATA_(ENABLE_CUDA|ENABLE_HIP|HIP_GFX906|PREFILL_MMQ|MMQ_KQUANTS|ORCA_Q4KS_MMQ|NATIVE_EXPERTS)" "$f"; done'
echo
echo "=== B) MMQ 库/目标是否产出 ==="
docker exec strata166 bash -lc 'ls -l /src/build-906/libstrata_mmq* /src/build-906/**/libstrata_mmq* 2>/dev/null; find /src/build-906 -name "*mmq*" -maxdepth 3 2>/dev/null | head -20'
echo
echo "=== C) 二进制里的 MMQ 符号 ==="
docker exec strata166 bash -lc 'nm -C /src/build-906/strata 2>/dev/null | grep -ci "mmq"; echo "---"; nm -C /src/build-906/strata 2>/dev/null | grep -i "prefill::mmq" | head -12'
echo
echo "=== D) 引擎日志里所有 mmq / MMQ / tile / fit 相关行 ==="
docker exec strata166 bash -lc 'grep -inE "mmq|tile|j_best|non-MMQ|FP16 prompt|fallback" /data/strata-ud-q4_k_xl.log | head -30'
echo
echo "=== E) 引擎日志全文（去重前 40 行，看启动期自述）==="
docker exec strata166 bash -lc 'head -40 /data/strata-ud-q4_k_xl.log'
echo
echo "=== F) 有无 --stats ==="
docker exec strata166 bash -lc '/src/build-906/strata --help 2>&1 | grep -iE "stats|verbose|trace|dump" | head -12'
'''

b = base64.b64encode(SC.encode('utf-8')).decode('ascii')
r = subprocess.run([SSH, '-o', 'BatchMode=yes', '-o', 'ConnectTimeout=10', '-i', KEY, HOST, 'base64 -d | bash'],
                   input=b.encode('ascii'), capture_output=True, timeout=420)
print(r.stdout.decode('utf-8', 'replace'))
e = r.stderr.decode('utf-8', 'replace')
if e.strip():
    print('--- STDERR ---')
    print(e[:600])
