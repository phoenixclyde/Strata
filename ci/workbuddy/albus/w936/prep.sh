#!/bin/bash
# W936 / R77 prep: 取 e1b27d54 全文 + 冲突范围 + 生产现场
set -u
echo "=== 生产现场 ==="
docker exec strata166-407 sh -lc 'curl -s -m 5 http://127.0.0.1:8090/health | head -c 60; echo;
md5sum /data/strata-huihui-ud-iq4_xs.json | cut -c1-32
P=$(pgrep -f "strata-0.1.55t --serve" | head -1)
md5sum /proc/$P/exe | cut -c1-32
grep VmLck /proc/$P/status'
docker inspect -f 'restarts={{.RestartCount}}' strata166-407

cd ~/strata166/pr/strata-fork || exit 1
echo
echo "=== e1b27d54 元信息 ==="
git log -1 --format='%h %ad %s' --date=short e1b27d54 2>/dev/null || echo "NOT FOUND"

echo
echo "=== 改动文件 ==="
git show --stat --format='' e1b27d54 2>/dev/null | head -20

echo
echo "=== 是否含 HIP 宏门控 ==="
git show e1b27d54 2>/dev/null | grep -cE 'STRATA_USE_HIP|STRATA_HIP_GFX906'

echo
echo "=== 补丁全文（前 200 行）==="
git show e1b27d54 2>/dev/null | head -200
