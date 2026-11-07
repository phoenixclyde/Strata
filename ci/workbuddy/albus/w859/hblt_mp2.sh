#!/bin/bash
# W859-B：把 src/msgpack/MessagePack.cpp 加进 tensilelite-host（这版 CMake 源列表漏了它，
#          而 hipblaslt 的 lazy 库路径引用了 LoadLibraryMapping / MessagePackLoadLibraryFile）
set -u
SRC=/home/albus/strata166/rocm-libs
OUT=/home/albus/strata166/data/w859_hblt
LOG=/home/albus/strata166/data/w859_msgpack2.log
IMG=strata-gfx906:0.2.9-101
: > "$LOG"
{
  echo "=== build start $(date +%F" "%T)"
  docker run --rm -v "$SRC":/src -v "$OUT":/out "$IMG" bash -lc '
set -u
export LD_LIBRARY_PATH=/opt/rocm/lib:${LD_LIBRARY_PATH:-}
F=/src/projects/hipblaslt/tensilelite/CMakeLists.txt
export TLF=$F
python3 - <<'PYX'
import io, os
p = os.environ["TLF"]
s = io.open(p, encoding="utf-8").read()
anchor = "    add_library(tensilelite-host)\n"
if "W859 msgpack sources" not in s:
    add = (anchor +
           "    # W859 msgpack sources\n"
           "    target_sources(tensilelite-host PRIVATE ${CMAKE_CURRENT_SOURCE_DIR}/src/msgpack/MessagePack.cpp)\n")
    assert anchor in s
    s = s.replace(anchor, add, 1)
    io.open(p, "w", encoding="utf-8").write(s)
    print("  patched")
else:
    print("  already")
PYX
import io, sys
p = sys.argv[1]
s = io.open(p, encoding="utf-8").read()
if "W859 msgpack sources" not in s:
    anchor = "    add_library(tensilelite-host)\n"
    add = (anchor +
           "    # W859 msgpack sources: 这版源列表漏了 src/msgpack/MessagePack.cpp，而 lazy 库路径要它的符号\n"
           "    target_sources(tensilelite-host PRIVATE ${CMAKE_CURRENT_SOURCE_DIR}/src/msgpack/MessagePack.cpp)\n")
    assert anchor in s
    s = s.replace(anchor, add, 1)
    io.open(p, "w", encoding="utf-8").write(s)
    print("  patched")
else:
    print("  already")
PYX
cd /out/build
cmake . > /out/cfg9.log 2>&1; echo "  cmake rc=$?"
nice -n 19 timeout 900 ninja -j 6 hipblaslt 2>&1 | tail -5
echo "--- .a msgpack 符号数:"; nm -C tensilelite/libtensilelite-host.a 2>/dev/null | grep -ci msgpack
echo "--- .so 未定义符号:"; nm -C library/libhipblaslt.so.1 2>/dev/null | grep -c " U .*TensileLite"
'
  echo "=== build end $(date +%F" "%T) rc=$?"
} >> "$LOG" 2>&1
sed -n "/=== build start/,\$p" "$LOG" | tail -12
