#!/bin/bash
F=/home/albus/strata166/data/strata-ud-iq4_xs.log
echo "=== 前 80 行里的启动信息 ==="
head -80 "$F" | grep -inE "expert|resident|slot|cache|RAM" | head -25
echo
echo "=== 含 experts 的句式（数字抹去后去重）==="
grep -oE "[0-9]+ experts[^,]*" "$F" | sed "s/[0-9]//g" | sort -u | head -12
echo
echo "=== resident RAM 行的全部取值（去重）==="
grep -oE "resident RAM:.{0,60}" "$F" | sort -u | head -8
echo
echo "=== 容器 402 启动日志里的专家/常驻行 ==="
docker logs strata166-402 2>&1 | head -60 | grep -inE "expert|resident|slot|RAM" | head -20
echo
echo "=== 容器 402 启动日志总行数 ==="
docker logs strata166-402 2>&1 | wc -l
echo
echo "=== 引擎 help 里与 expert 有关的开关 ==="
docker exec strata166-402 bash -lc "/src/build-906/strata --help 2>&1 | grep -iE 'expert|resident|lru' | head -20"
