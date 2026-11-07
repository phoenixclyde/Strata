#!/bin/bash
set -u
W=/home/albus/strata166/work/r77
R=/home/albus/strata166/pr/strata-fork
mkdir -p ~/strata166/patches ~/strata166/w936

echo "=== 1) 生成可用于重建的合并补丁（相对主线 d963c791） ==="
cd "$W" || exit 1
rm -rf .git
diff -ruN --exclude=.git "$R" "$W" > ~/strata166/patches/r77_fatal_gpu_on_mainline.patch 2>/dev/null
wc -l ~/strata166/patches/r77_fatal_gpu_on_mainline.patch
echo "--- 涉及文件 ---"
grep -E "^\+\+\+ " ~/strata166/patches/r77_fatal_gpu_on_mainline.patch | sed 's/^+++ //' | head -10

echo
echo "=== 2) 关键文件指纹 ==="
md5sum "$W/src/program/generate.cpp" "$W/serve/server.py" "$W/serve/test_fatal_gpu_restart.py" | sed "s#$W/##"

echo
echo "=== 3) 二进制与配置归档 ==="
cp -f /home/albus/strata166/gfx029-build/strata ~/strata166/w936/strata-cf2ba243 2>/dev/null && echo "binary archived"
docker cp strata166-407:/data/strata-huihui-ud-iq4_xs.json ~/strata166/w936/cfg_r77.json >/dev/null 2>&1 && echo "config archived"

echo
echo "=== 4) 生产最终状态 ==="
docker exec strata166-407 sh -lc 'curl -s -m 5 http://127.0.0.1:8090/health | head -c 70; echo
md5sum /data/strata-huihui-ud-iq4_xs.json | cut -c1-32
md5sum /src/serve/server.py | cut -c1-32
P=$(pgrep -f "strata-0.1.55t --serve" | head -1)
md5sum /proc/$P/exe | cut -c1-32
grep VmLck /proc/$P/status
tr "\0" "\n" < /proc/$P/environ | grep -c INJECT_FATAL'
docker inspect -f 'restarts={{.RestartCount}} ulimits={{json .HostConfig.Ulimits}}' strata166-407
