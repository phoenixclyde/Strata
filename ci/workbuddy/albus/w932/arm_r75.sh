#!/bin/bash
# W932 R75 A 臂：R66 三补丁(9d9cbe17) + --prefill auto:16384 + 三个 env
set -u
C="docker exec strata166-407"
CFG=/data/strata-huihui-ud-iq4_xs.json
NEW=~/strata166/gfx029-build/strata

echo "=== 0. 备份容器内当前二进制与 config ==="
$C sh -c "cp /data/bin/strata-0.1.55t /data/bin/strata.bak-a97f4479 && ls -l /data/bin/strata.bak-a97f4479 | awk '{print \"  bak size=\"\$5}'"
$C md5sum /data/bin/strata.bak-a97f4479
$C cp $CFG ${CFG}.bak_w932
$C md5sum $CFG

echo "=== 1. 装实验二进制 ==="
docker cp $NEW strata166-407:/data/bin/strata-0.1.55t.new >/dev/null 2>&1
$C sh -c "chmod +x /data/bin/strata-0.1.55t.new && mv /data/bin/strata-0.1.55t.new /data/bin/strata-0.1.55t"
$C md5sum /data/bin/strata-0.1.55t

echo "=== 2. 改 config：--prefill auto:16384 + 三个 env ==="
$C python3 -c "
import json
p='$CFG'
d=json.load(open(p))
i=d['args'].index('--prefill')
old=d['args'][i+1]
d['args'][i+1]='auto:16384'
for k in ('STRATA_PF_GROUP_SCRATCH','STRATA_PREFILL_ROUTED_STREAM','STRATA_PF_HC_REGION'):
    d['env'][k]='1'
json.dump(d,open(p,'w'),indent=2,ensure_ascii=False)
print('  prefill: %s -> auto:16384' % old)
print('  env count =', len(d['env']))
print('  tuned =', d['env'].get('STRATA_GFX906_TUNED'))
"

echo "=== 3. 重启 ==="
docker restart strata166-407
for i in $(seq 1 70); do
  s=$(curl -s -m 3 http://127.0.0.1:8090/health 2>/dev/null)
  case "$s" in *'"ok"'*) echo "UP after $((i*5))s"; break;; esac
  sleep 5
done

echo "=== 4. 路径断言：borrows 是否降到 ~2030 ==="
$C sh -c "grep -E 'prompt chunk auto|borrows [0-9]+ CUDA0|expert cache [0-9]+ slots|VRAM free with everything' /data/strata-huihui-ud-iq4_xs.log | tail -4"
echo "--- routed stream 是否确认生效 ---"
$C sh -c "grep -E 'PREFILL_ROUTED_STREAM=1' /data/strata-huihui-ud-iq4_xs.log | tail -1" | cut -c1-190
