#!/bin/bash
# W935：装 PLE 提限补丁（干净版 8e92c662）到生产
set -u
C="docker exec strata166-407"
CFG=/data/strata-huihui-ud-iq4_xs.json
NEW=~/strata166/gfx029-build/strata

echo "=== 0. 备份当前引擎 ==="
$C sh -c "cp /data/bin/strata-0.1.55t /data/bin/strata.bak-a97f4479 && md5sum /data/bin/strata.bak-a97f4479"

echo "=== 1. 装新二进制 ==="
docker cp $NEW strata166-407:/data/bin/strata-0.1.55t.new >/dev/null 2>&1
$C sh -c "chmod +x /data/bin/strata-0.1.55t.new && mv /data/bin/strata-0.1.55t.new /data/bin/strata-0.1.55t"
$C md5sum /data/bin/strata-0.1.55t
$C sh -c "ls -l /data/bin/strata-0.1.55t | awk '{print \"  size=\", \$5}'"

echo "=== 2. 重启 ==="
docker restart strata166-407
for i in $(seq 1 70); do
  s=$(curl -s -m 3 http://127.0.0.1:8090/health 2>/dev/null)
  case "$s" in *'"ok"'*) echo "UP after $((i*5))s"; break;; esac
  sleep 5
done

echo "=== 3. 关键验证：unlimited 下不应打印 raised to；PLE 应锁住 ==="
$C sh -c "P=\$(pgrep -f 'strata-0.1.55t --serve'|head -1)
echo '--- ulimit ---'
grep -i 'max locked' /proc/\$P/limits
echo '--- PLE 相关日志（本次 run）---'
tail -3000 /data/strata-huihui-ud-iq4_xs.log | grep -iE 'PLE table|may lock only|raised to' | tail -6
echo '--- VmLck ---'
grep VmLck /proc/\$P/status"
