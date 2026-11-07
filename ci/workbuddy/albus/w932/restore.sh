#!/bin/bash
# W932 C 臂：完全恢复原生产（a97f4479 + auto + 无三 env），并复测 64K 以判定 71.130 是否可重复
set -u
C="docker exec strata166-407"
CFG=/data/strata-huihui-ud-iq4_xs.json

echo "=== 1. 恢复二进制 a97f4479 ==="
$C sh -c "cp /data/bin/strata.bak-a97f4479 /data/bin/strata-0.1.55t.restore && chmod +x /data/bin/strata-0.1.55t.restore && mv /data/bin/strata-0.1.55t.restore /data/bin/strata-0.1.55t"
$C md5sum /data/bin/strata-0.1.55t

echo "=== 2. 恢复 config ==="
$C cp ${CFG}.bak_w932 $CFG
$C md5sum $CFG
$C python3 -c "
import json
d=json.load(open('$CFG'))
a=d['args']
print('  prefill =', a[a.index('--prefill')+1])
print('  kv =', a[a.index('--kv')+1])
print('  env =', sorted(d['env']))
"

echo "=== 3. 重启 ==="
docker restart strata166-407
for i in $(seq 1 70); do
  s=$(curl -s -m 3 http://127.0.0.1:8090/health 2>/dev/null)
  case "$s" in *'"ok"'*) echo "UP after $((i*5))s"; break;; esac
  sleep 5
done
echo "=== 4. 确认回到原状（borrows 应 1578） ==="
$C sh -c "grep -E 'prompt chunk auto|borrows [0-9]+ CUDA0|expert cache [0-9]+ slots' /data/strata-huihui-ud-iq4_xs.log | tail -3"
