#!/bin/bash
# W863 · 只用 ninja 自己列出的三条命令：编译 native_mmvq.cu.o → 重归档 libstrata_kernels.a → 链接 strata
# build.ninja 不重生成（/llama.cpp 挂载缺失，见 albus/w863/d7_cfgerr.sh）
set -u
S=/home/albus/strata166/pr/strata-fork
B=/home/albus/strata166/gfx029-build
IMG=strata-gfx906:0.2.9-101

docker rm -f w863build >/dev/null 2>&1
docker run -d --name w863build --security-opt label=disable \
  -v "$S":/src -v "$B":/out "$IMG" bash -lc '
set -u
cd /out || exit 1
md5sum build.ninja
ninja -t commands strata > /out/_w863_all.txt 2>/dev/null || { echo "NINJA -t commands FAILED"; exit 1; }
echo "total commands: $(wc -l < /out/_w863_all.txt)"
L1=$(grep -n "native_mmvq.cu.o" /out/_w863_all.txt | grep -- "-x hip -c" | head -1 | cut -d: -f1)
L2=$(grep -n "llvm-ar qc libstrata_kernels.a" /out/_w863_all.txt | head -1 | cut -d: -f1)
L3=$(wc -l < /out/_w863_all.txt)
echo "compile line=$L1  archive line=$L2  link line=$L3"
[ -z "$L1" ] && { echo "COMPILE LINE NOT FOUND"; exit 1; }
[ -z "$L2" ] && { echo "ARCHIVE LINE NOT FOUND"; exit 1; }
sed -n "${L1}p;${L2}p;${L3}p" /out/_w863_all.txt > /out/_w863_step.sh
echo "=== running the three commands (compile ~8-10 min) ==="
time bash -e /out/_w863_step.sh
echo "STEP_RC=$?"
md5sum build.ninja
ls -l strata libstrata_kernels.a
' 2>&1 | tail -3
sleep 20
docker inspect w863build --format 'status={{.State.Status}}' 2>/dev/null
docker logs w863build 2>&1 | tail -6
