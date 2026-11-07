#!/bin/bash
# W839-20 增量重编（只改 generate.cpp -> 重编 + 重链接）
S=/home/albus/strata166/src028
date +%H:%M:%S
docker rm -f b028r4 >/dev/null 2>&1
docker run -d --name b028r4 --security-opt label=disable \
  -v "$S":/src -w /src strata-gfx906:0.2.8 \
  bash -lc 'ninja -C /src/build-028r -j10 > /src/build-028r4.log 2>&1; echo "EXIT=$?" >> /src/build-028r4.log' >/dev/null
sleep 12
echo "--- 前 12 行 ---"
head -12 $S/build-028r4.log 2>/dev/null | cut -c1-150
for i in $(seq 1 40); do
  grep -q 'EXIT=' $S/build-028r4.log 2>/dev/null && break
  sleep 10
done
echo "--- 结尾 ---"
tail -4 $S/build-028r4.log | cut -c1-150
echo "=== 证据 ==="
B=$S/build-028r
echo "generate.cpp.o 引用 apply_arch_defaults: $(nm -C $B/CMakeFiles/strata.dir/src/program/generate.cpp.o 2>/dev/null | grep -c apply_arch_defaults)"
echo "二进制 MI50-class: $(grep -a -c -F 'MI50-class' $B/strata 2>/dev/null)"
echo "二进制 exact speed switches: $(grep -a -c -F 'exact speed switches' $B/strata 2>/dev/null)"
echo "二进制 gfx_arch_is_gfx906 符号: $(nm -C $B/strata 2>/dev/null | grep -c gfx_arch_is_gfx906)"
ls -la $B/strata | cut -c1-80
