#!/bin/bash
# W861-AF: 把 .zlib 解压成未压缩 .dat（引擎优先找 .dat），再看是否还报 Unknown key
set -u
R=/home/albus/strata166
SRC=$R/data/w861_lib906d
NEW=$R/data/w861_lib906e
LOG=$R/data/w861_probe_unz.log
: > "$LOG"
{
echo "=== unz start $(date -u +%FT%TZ) ==="
rm -rf "$NEW"; mkdir -p "$NEW"
docker run --rm -v "$SRC":/src:ro -v "$NEW":/out -v "$R/data/w858_hblt":/g858:ro \
  strata-gfx906:0.2.9-101 bash -lc '
set -u
export PYTHONPATH=/g858/pylib
python3 - <<PY
import zlib, os, glob, shutil
for f in glob.glob("/src/*.zlib"):
    base = os.path.basename(f)[:-5]          # 去掉 .zlib
    out = os.path.join("/out", base)
    raw = zlib.decompress(open(f, "rb").read())
    open(out, "wb").write(raw)
    print("wrote", base, len(raw), "bytes")
for f in glob.glob("/src/*.hsaco"):
    shutil.copy2(f, os.path.join("/out", os.path.basename(f)))
    print("copied", os.path.basename(f))
PY
ls -la /out
'
echo "--- probe ---"
docker run --rm --device /dev/kfd --device /dev/dri --group-add video \
  -v "$NEW":/v20/lib906:ro -v "$R/data/w859_hblt/build/library":/lt:ro \
  -v /home/albus/w861_probe4.cpp:/p4.cpp:ro -v /home/albus/w861_open_hook.c:/hook.c:ro \
  strata-gfx906:0.2.9-101 bash -lc '
set -u
export PATH=/opt/rocm/bin:/opt/rocm/llvm/bin:/usr/bin:/bin
export LD_LIBRARY_PATH=/opt/rocm/lib
gcc -shared -fPIC -O1 -o /tmp/oh.so /hook.c -ldl 2>/dev/null
hipcc -O2 -std=c++17 /p4.cpp -o /tmp/p4 -lhipblaslt 2>/dev/null
export LD_LIBRARY_PATH=/lt:/opt/rocm/lib
echo "--- files ---"; ls /v20/lib906
LD_PRELOAD=/tmp/oh.so timeout 180 /tmp/p4 /v20/lib906 256 5120 2560 2>&1 \
  | grep -viE "LLVM option|Did you mean" | head -30
' 2>&1
echo "=== unz end $(date -u +%FT%TZ) ==="
} >> "$LOG" 2>&1
sed -n "/=== unz start/,\$p" "$LOG" | tail -40
