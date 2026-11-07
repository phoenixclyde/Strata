# -*- coding: utf-8 -*-
"""在 166 上反汇编 MMQ 目标文件，确认 gfx906 代码里真的用了 v_dot4_i32_i8（硬件 dp4a）而非 4 次循环。
同时偷一眼对拍进度。"""
import base64, os, subprocess, sys, time
sys.stdout.reconfigure(encoding='utf-8')

KEY = os.path.expanduser('~/.ssh/id_ed25519_workbuddy')
SSH = r'C:\Program Files\Git\usr\bin\ssh.exe'
HOST = 'albus@192.168.50.166'

SC = r'''
set +e
echo "=== 对拍进度（本机日志尾部）==="
tail -12 /home/albus/strata166/logs/../data/serve-run.log 2>/dev/null | tail -4
echo
echo "=== 0.1.40.1 容器内：找 mmq 目标文件 ==="
docker exec strata166-401 bash -lc '
set +e
OBJ=$(find /src/build-906 -name "*mmq-instance-q4_k.cu.o" | head -1)
echo "obj = $OBJ"
if [ -n "$OBJ" ]; then
  ls -l "$OBJ"
  TOOL=$(command -v llvm-objdump || ls /opt/rocm/llvm/bin/llvm-objdump 2>/dev/null | head -1)
  echo "tool = $TOOL"
  if [ -n "$TOOL" ]; then
    echo "--- v_dot4_i32_i8 出现次数 ---"
    "$TOOL" -d --arch-name=gfx906 "$OBJ" 2>/dev/null | grep -c "v_dot4_i32_i8"
    echo "--- sdot4 / dot4 相关指令样例 ---"
    "$TOOL" -d --arch-name=gfx906 "$OBJ" 2>/dev/null | grep -oE "v_dot[0-9a-z_]*" | sort | uniq -c | sort -rn | head -8
    echo "--- 对比：SDWA 风格的选择/符号扩展（RDNA1 退化路径会用 lshr/lshl+bfe）---"
    "$TOOL" -d --arch-name=gfx906 "$OBJ" 2>/dev/null | grep -oE "\bv_(bfe|perm|alignbit|add_i32|mad_i32)\b" | sort | uniq -c | sort -rn | head -6
  fi
fi
'
echo
echo "=== 显存/进程快照 ==="
rocm-smi --showmemuse 2>/dev/null | grep -i vram | head -2
pgrep -af "strata serve|server.py" | head -4
'''
b = base64.b64encode(SC.encode('utf-8')).decode('ascii')
r = subprocess.run([SSH, '-o', 'BatchMode=yes', '-o', 'ConnectTimeout=10',
                    '-o', 'ServerAliveInterval=30', '-i', KEY, HOST, 'base64 -d | bash'],
                   input=b.encode('ascii'), capture_output=True, timeout=600)
print(r.stdout.decode('utf-8', 'replace'))
e = r.stderr.decode('utf-8', 'replace')
if e.strip():
    print('ERR', e[:400])
