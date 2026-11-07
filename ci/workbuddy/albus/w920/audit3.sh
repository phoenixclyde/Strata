#!/bin/bash
cd ~/strata166/pr/strata-fork || exit 1
echo "=== trace_on 完整实现 ==="
sed -n '12188,12230p' src/program/generate.cpp

echo
echo "=== marker 文件路径常量 ==="
sed -n '12188,12230p' src/program/generate.cpp | grep -nE "marker|path|fopen|stat|getenv" 

echo
echo "=== 容器内是否存在该 marker ==="
docker exec strata166-407 sh -c 'for f in /tmp/strata_trace /tmp/strata-trace /data/strata_trace /data/trace /tmp/trace /data/.trace /src/.trace; do [ -e "$f" ] && echo "EXISTS $f ($(stat -c%s $f) B)"; done; echo "(扫描完毕)"'
