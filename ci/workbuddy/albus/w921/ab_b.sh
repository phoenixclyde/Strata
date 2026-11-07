#!/bin/bash
set -u
BD=~/strata166/data/bin
B=~/strata166/gfx029-build
CFG=/data/strata-huihui-ud-iq4_xs.json

echo "=== 1. 备份生产二进制 ==="
ls -l $BD/strata-0.1.55t
md5sum $BD/strata-0.1.55t
cp -a $BD/strata-0.1.55t $BD/strata-0.1.55t.bak-w921
echo "backup -> $(md5sum $BD/strata-0.1.55t.bak-w921 | cut -c1-32)"

echo
echo "=== 2. 装入实验二进制 ==="
cp $B/strata $BD/strata-0.1.55t.new
md5sum $BD/strata-0.1.55t.new
chmod +x $BD/strata-0.1.55t.new
mv $BD/strata-0.1.55t.new $BD/strata-0.1.55t
echo "now: $(md5sum $BD/strata-0.1.55t | cut -c1-32)"

echo
echo "=== 3. 加三个 env 到 config ==="
docker exec strata166-407 cp $CFG ${CFG}.bak-w921
docker exec strata166-407 python3 -c "
import json
p='$CFG'
d=json.load(open(p))
d['env']['STRATA_PF_GROUP_SCRATCH']='1'
d['env']['STRATA_PREFILL_ROUTED_STREAM']='1'
d['env']['STRATA_PF_HC_REGION']='1'
json.dump(d,open(p,'w'),indent=2,ensure_ascii=False)
print('env count:', len(d['env']))
print('added:', [k for k in d['env'] if 'PF_' in k or 'ROUTED' in k])
"

echo
echo "=== 4. 重启 ==="
docker restart strata166-407 >/dev/null && echo RESTARTED

echo "=== 5. 等 health ==="
for i in $(seq 1 84); do
  s=$(curl -s -m 3 http://127.0.0.1:8090/health 2>/dev/null)
  case "$s" in *'"ok"'*) echo "UP after $((i*5))s"; break;; esac
  sleep 5
done

echo
echo "=== 6. 三个开关是否真的生效（日志）==="
docker exec strata166-407 sh -c "tail -400 /data/strata-huihui-ud-iq4_xs.log | grep -iE 'GROUP_SCRATCH|ROUTED_STREAM|HC_REGION|prefill:' | cut -c1-170"
