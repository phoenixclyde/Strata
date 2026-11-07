#!/bin/bash
# W931 B 臂：--prefill auto -> auto:16384（gfx12 的默认值，R70 要借的那条）
set -u
C="docker exec strata166-407"
CFG=/data/strata-huihui-ud-iq4_xs.json

$C cp $CFG ${CFG}.bak_w931
$C md5sum $CFG

echo "=== 改 --prefill ==="
$C python3 -c "
import json
p='$CFG'
d=json.load(open(p))
i=d['args'].index('--prefill')
old=d['args'][i+1]
d['args'][i+1]='auto:16384'
json.dump(d,open(p,'w'),indent=2,ensure_ascii=False)
print('prefill: %s -> %s' % (old, d['args'][i+1]))
"

echo "=== 重启 ==="
docker restart strata166-407
for i in $(seq 1 70); do
  s=$(curl -s -m 3 http://127.0.0.1:8090/health 2>/dev/null)
  case "$s" in *'"ok"'*) echo "UP after $((i*5))s"; break;; esac
  sleep 5
done

echo "=== 关键布局（chunk 是否真变 16384 / 显存是否够） ==="
$C sh -c "grep -E 'prompt chunk auto|prompts longer than|WARNING: prompt chunk|expert cache [0-9]+ slots|VRAM free with everything' /data/strata-huihui-ud-iq4_xs.log | tail -5" 2>&1
$C sh -c "tr '\0' ' ' < /proc/\$(pgrep -f 'strata-0.1.55t --serve'|head -1)/cmdline | grep -o '\-\-prefill [a-z0-9:]*'"
