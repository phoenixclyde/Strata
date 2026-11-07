# -*- coding: utf-8 -*-
"""prefill 期间 GPU 利用率实测：跑一个 M 档请求，同时每 1s 采 rocm-smi --showuse。
用途：验证 W784 记录的「prefill 229.6s GPU util = 0%」是否成立（netdata 采样可能错过脉冲）。
"""
import subprocess, base64, sys, time

HOST = "albus@192.168.50.166"

def run(script, timeout=900):
    p = subprocess.run(["ssh", "-o", "BatchMode=yes", HOST, "base64 -d | bash"],
                       input=base64.b64encode(script.encode()),
                       stdout=subprocess.PIPE, stderr=subprocess.STDOUT, timeout=timeout)
    return p.stdout.decode("utf-8", "replace")

stage = sys.argv[1] if len(sys.argv) > 1 else "M"
runs = sys.argv[2] if len(sys.argv) > 2 else "1"

s = r'''
set -u
cd /home/albus/strata166/tmp
S=/home/albus/strata166/data/_gpupoll.txt
rm -f $S
( while true; do
    u=$(/opt/rocm/bin/rocm-smi --showuse 2>/dev/null | grep -oE 'GPU use \(%\): [0-9]+' | grep -oE '[0-9]+$' | head -1)
    [ -z "$u" ] && u=NA
    echo "$(date +%s) $u" >> $S
    sleep 1
  done ) &
POLL=$!
T0=$(date +%s)
python3 w776_bench.py __STAGE__ __RUNS__ 2>&1 | tail -3
T1=$(date +%s)
kill $POLL 2>/dev/null
echo "=== poll window: $T0 .. $T1 ($((T1-T0))s) ==="
# 按时间对齐：bench 输出给出 prompt_ms / decode_tps，用 wall 反推
python3 - <<'PY'
import os
rows=[]
for ln in open('/home/albus/strata166/data/_gpupoll.txt'):
    p=ln.split()
    if len(p)==2: rows.append((int(p[0]), p[1]))
if not rows:
    print('NO POLL DATA'); raise SystemExit
vals=[r[1] for r in rows]
import collections
c=collections.Counter(vals)
print('samples', len(rows), 'range', rows[0][0], rows[-1][0])
print('util histogram (top 12):', c.most_common(12))
num=[int(v) for v in vals if v.isdigit()]
if num:
    num.sort()
    print('median %d  p10 %d  p90 %d  max %d  zero_share %.0f%%' % (
        num[len(num)//2], num[len(num)//10], num[int(len(num)*0.9)], num[-1],
        100.0*sum(1 for v in num if v==0)/len(num)))
PY
'''.replace('__STAGE__', stage).replace('__RUNS__', runs)

print(run(s, timeout=1200))
