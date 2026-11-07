#!/bin/bash
# W861-AI: 补 mxScaleLayoutForArchName 最小实现，编完 tensilelite-client
set -u
R=/home/albus/strata166
OUTD=$R/data/w859_hblt
LOG=$R/data/w861_client_final.log
: > "$LOG"
{
echo "=== client final start $(date -u +%FT%TZ) ==="
docker run --rm --cpus=12 -v "$R/rocm-libs":/src -v "$OUTD":/out \
  -v /home/albus/w861_mx_stub.cpp:/mx_stub.cpp:ro \
  strata-gfx906:0.2.9-101 bash -lc '
set -u
export PATH=/opt/rocm/bin:/opt/rocm/llvm/bin:/usr/bin:/bin
export LD_LIBRARY_PATH=/opt/rocm/lib
echo "--- 放进 client/src 并加进 CMake ---"
cp /mx_stub.cpp /src/projects/hipblaslt/tensilelite/client/src/mx_stub.cpp
G=/src/projects/hipblaslt/tensilelite/client/CMakeLists.txt
if ! grep -q mx_stub.cpp "$G"; then
  python3 - <<PY
p = "$G"
s = open(p).read()
anchor = "add_library(tensilelite-client-common STATIC)"
# 先清掉上一轮错误插入的裸行
s = s.replace("\n  src/mx_stub.cpp   # _W861: mxDataGen 最小实现（gfx906 不需要 MX 布局）", "")
if "mx_stub.cpp" not in s:
    s = s.replace(anchor, anchor + "\ntarget_sources(tensilelite-client-common PRIVATE ${CMAKE_CURRENT_SOURCE_DIR}/src/mx_stub.cpp)  # _W861")
    open(p, "w").write(s)
    print("CMakeLists patched (target_sources)")
else:
    print("already")
PY
fi
grep -n "mx_stub" "$G" | head -3

cd /out/build
echo "--- rebuild ---"
nice -n 19 timeout 1800 ninja tensilelite-client -j 12 2>&1 | tail -10
echo "--- 产物 ---"
ls -la /out/build/tensilelite/client/tensilelite-client 2>/dev/null
'
echo "=== client final end $(date -u +%FT%TZ) ==="
} >> "$LOG" 2>&1
sed -n "/=== client final start/,\$p" "$LOG" | tail -25
