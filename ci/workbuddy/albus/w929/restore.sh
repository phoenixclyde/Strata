#!/bin/bash
# W929 恢复：回到 k8v4 + 撤 STRATA_PREFILL_TIMING（config 回到 51ef8837）
set -u
C="docker exec strata166-407"
CFG=/data/strata-huihui-ud-iq4_xs.json

echo "=== 1. 从备份恢复 ==="
$C cp ${CFG}.bak_w929 $CFG
$C md5sum $CFG
$C python3 -c "
import json
d=json.load(open('$CFG'))
print('kv =', d['args'][d['args'].index('--kv')+1])
print('env =', sorted(d['env']))
print('keys =', len(d['args']))
"

echo "=== 2. 重启 ==="
docker restart strata166-407
echo "=== 3. 等健康 ==="
for i in $(seq 1 70); do
  s=$(curl -s -m 3 http://127.0.0.1:8090/health 2>/dev/null)
  case "$s" in *'"ok"'*) echo "UP after $((i*5))s"; break;; esac
  sleep 5
done

echo "=== 4. 验证回到原状 ==="
$C sh -c "grep -E 'expert cache [0-9]+ slots|VRAM free with everything' /data/strata-huihui-ud-iq4_xs.log | tail -2"
$C sh -c "tr '\0' ' ' < /proc/\$(pgrep -f 'strata-0.1.55t --serve'|head -1)/cmdline | grep -o '\-\-kv [a-z0-9_]*'"
$C sh -c "P=\$(pgrep -f 'strata-0.1.55t --serve'|head -1); tr '\0' '\n' < /proc/\$P/environ | grep -c PREFILL_TIMING"
$C sh -c "md5sum /proc/\$(pgrep -f 'strata-0.1.55t --serve'|head -1)/exe | cut -c1-32"
