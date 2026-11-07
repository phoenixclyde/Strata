#!/bin/bash
# W861-I: 造 .dat 主库 + mapping + 去 xnack 的 hsaco，探针复验
set -u
R=/home/albus/strata166
LIB=$R/data/w861_lib906
CACHE=$(find $R/data/w859_hblt/gen16 -type d -path "*caches/*/source/library/gfx906" | head -1)
LOG=$R/data/w861_probe_final2.log
: > "$LOG"
{
echo "=== probe2 start $(date -u +%FT%TZ) ==="
rm -rf "$LIB"; mkdir -p "$LIB"
docker run --rm -v /home/albus/strata166/rocm-libs:/src:ro -v "$R/data/w859_hblt":"$R/data/w859_hblt":ro \
  -v "$LIB":/out -v /home/albus/w861_make_lib.py:/mk.py:ro \
  -v "$R/data/w858_hblt":/g858:ro strata-gfx906:0.2.9-101 bash -lc "
set -u
export PYTHONPATH=/g858/pylib:/g858/rocisa-install:/src/projects/hipblaslt/tensilelite
python3 /mk.py '$CACHE' /out 2>&1
"
echo "=== probe run ==="
docker run --rm --device /dev/kfd --device /dev/dri --group-add video \
  -v "$LIB":/v20/lib906:ro -v "$R/data/w858_hblt":/probe:ro \
  strata-gfx906:0.2.9-101 bash -lc '
set -u
export LD_LIBRARY_PATH=/opt/rocm/lib:${LD_LIBRARY_PATH:-}
export HIPBLASLT_TENSILE_LIBPATH=/v20/lib906
cd /probe
echo "--- files ---"; ls /v20/lib906
echo "===== probe3 ====="
timeout 120 ./probe3 2>&1 | tail -18
' 2>&1
echo "=== probe2 end $(date -u +%FT%TZ) ==="
} >> "$LOG" 2>&1
sed -n "/=== probe2 start/,\$p" "$LOG" | tail -45
