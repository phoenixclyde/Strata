#!/bin/bash
# W859-B：把 tensilelite-host 真正带进 libhipblaslt.so（roc:: ALIAS 没生效 + 若需 whole-archive）
set -u
SRC=/home/albus/strata166/rocm-libs
OUT=/home/albus/strata166/data/w859_hblt
LOG=/home/albus/strata166/data/w859_link.log
IMG=strata-gfx906:0.2.9-101
: > "$LOG"
{
  echo "=== link start $(date +%F" "%T)"
  docker run --rm -v "$SRC":/src -v "$OUT":/out "$IMG" bash -lc '
set -u
export LD_LIBRARY_PATH=/opt/rocm/lib:${LD_LIBRARY_PATH:-}
F=/src/projects/hipblaslt/CMakeLists.txt
cp -n $F /out/CMakeLists.txt.orig 2>/dev/null || true
python3 - "$F" <<PYX
import io, sys
p = sys.argv[1]
s = io.open(p, encoding="utf-8").read()
if "W859 whole-archive" not in s:
    old = "            roc::tensilelite-host\n"
    new = ("            tensilelite-host\n"
           "            -Wl,--whole-archive /out/build/tensilelite/libtensilelite-host.a -Wl,--no-whole-archive  # W859 whole-archive\n")
    assert old in s, "anchor missing"
    s = s.replace(old, new, 1)
    io.open(p, "w", encoding="utf-8").write(s)
    print("  patched")
else:
    print("  already patched")
PYX
cd /out/build
cmake . > /out/cfg7.log 2>&1; echo "  cmake rc=$?"
nice -n 19 timeout 600 ninja -j 4 hipblaslt 2>&1 | tail -4
echo "--- 符号（T 已定义 / U 未定义）:"
nm -C /out/build/library/libhipblaslt.so.1 | grep "LoadLibraryMapping" | head -2
'
  echo "=== link end $(date +%F" "%T) rc=$?"
} >> "$LOG" 2>&1
sed -n "/=== link start/,\$p" "$LOG" | tail -14
