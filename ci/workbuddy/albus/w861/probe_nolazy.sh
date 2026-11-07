#!/bin/bash
# W861-K: 非 lazy 库 + 自编 hipblaslt -> 探针
set -u
R=/home/albus/strata166
LIB=$R/data/w861_lib906b
CACHE=$(find $R/data/w859_hblt/gen16 -type d -path "*caches/*/source/library/gfx906" | head -1)
OUTD=$R/data/w859_hblt
LOG=$R/data/w861_probe_nolazy.log
: > "$LOG"
{
echo "=== probe nolazy start $(date -u +%FT%TZ) ==="
rm -rf "$LIB"; mkdir -p "$LIB"
docker run --rm -v "$R/rocm-libs":/src:ro -v "$R/data/w859_hblt":"$R/data/w859_hblt":ro \
  -v "$LIB":/out -v /home/albus/w861_make_lib2.py:/mk2.py:ro -v "$R/data/w858_hblt":/g858:ro \
  strata-gfx906:0.2.9-101 bash -lc "
set -u
export PYTHONPATH=/g858/pylib:/g858/rocisa-install:/src/projects/hipblaslt/tensilelite
python3 /mk2.py '$CACHE' /out
"
echo "--- libhipblaslt (自编, LAZY_LOAD=OFF) ---"
grep -i 'LAZY_LOAD' $OUTD/build/CMakeCache.txt | head -2
ls -la $OUTD/build/library/libhipblaslt.so.1.4
echo "--- probe ---"
docker run --rm --device /dev/kfd --device /dev/dri --group-add video \
  -v "$LIB":/v20/lib906:ro -v "$R/data/w858_hblt":/probe:ro \
  -v "$OUTD/build/library":/lt:ro \
  strata-gfx906:0.2.9-101 bash -lc '
set -u
export LD_LIBRARY_PATH=/lt:/opt/rocm/lib:${LD_LIBRARY_PATH:-}
export HIPBLASLT_TENSILE_LIBPATH=/v20/lib906
cd /probe
echo "--- files ---"; ls /v20/lib906
echo "--- lib in use ---"; ldd ./probe3 2>/dev/null | grep -i hipblaslt
echo "===== probe3 ====="
timeout 180 ./probe3 2>&1 | tail -20
' 2>&1
echo "=== probe nolazy end $(date -u +%FT%TZ) ==="
} >> "$LOG" 2>&1
sed -n "/=== probe nolazy start/,\$p" "$LOG" | tail -45
