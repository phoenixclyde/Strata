#!/bin/bash
# W839-02 增量编译：把分支的 arch_defaults 改动编译进 v0.2.8 基底的构建树
S=/home/albus/strata166/src028
B=/home/albus/strata166/data/bin
date +%H:%M:%S
echo "=== 编译前：源文件指纹 ==="
md5sum $S/src/core/arch_defaults.cpp $S/CMakeLists.txt | sed 's#/home/albus/strata166/##'
ls -la $S/build-028r/strata 2>/dev/null | cut -c1-80

echo "=== 用 ninja 试运行看要重编哪些 ==="
docker rm -f b028r3 >/dev/null 2>&1
docker run --rm --security-opt label=disable -v "$S":/src -w /src strata-gfx906:0.2.8 \
  bash -lc 'cd /src && ninja -C build-028r -n 2>&1 | head -12' 2>&1 | head -14

echo "=== 启动增量编译（后台） ==="
docker rm -f b028r3 >/dev/null 2>&1
docker run -d --name b028r3 --security-opt label=disable \
  -v "$S":/src -w /src strata-gfx906:0.2.8 \
  bash -lc 'ninja -C /src/build-028r -j10 > /src/build-028r3.log 2>&1; echo "EXIT=$?" >> /src/build-028r3.log' >/dev/null
sleep 20
docker ps --format '{{.Names}} {{.Status}}' | grep b028r3 || echo "build container not running"
tail -5 $S/build-028r3.log 2>/dev/null | cut -c1-160
