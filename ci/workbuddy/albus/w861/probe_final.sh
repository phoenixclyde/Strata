#!/bin/bash
# W861-H: 用 gen16 已 codegen 成功的库，按 tensile_host.cpp 的命名约定摆好，探针验 algos
set -u
R=/home/albus/strata166
LIB=$R/data/w861_lib906
CACHE=$(find $R/data/w859_hblt/gen16 -type d -path "*caches/*/source/library/gfx906" | head -1)
LOG=$R/data/w861_probe_final.log
: > "$LOG"
{
echo "=== probe final start $(date -u +%FT%TZ) ==="
echo "cache dir: $CACHE"
ls -la "$CACHE"
rm -rf "$LIB"; mkdir -p "$LIB"
cp "$CACHE"/*.hsaco "$LIB"/ 2>/dev/null
cp "$CACHE"/TensileLibrary.yaml "$LIB"/ 2>/dev/null
# 两种命名都摆：非 lazy 与 lazy，yaml 与 dat
for n in gfx906; do
  [ -f "$LIB/TensileLibrary.yaml" ] && cp "$LIB/TensileLibrary.yaml" "$LIB/TensileLibrary_$n.yaml"
  [ -f "$LIB/TensileLibrary.yaml" ] && cp "$LIB/TensileLibrary.yaml" "$LIB/TensileLibrary_lazy_$n.yaml"
done
# 有的分支找 .dat；把 yaml 用引擎自己的 write 转一份 msgpack
ls -la "$LIB"
echo "=== probe (3 variants) ==="
docker run --rm --device /dev/kfd --device /dev/dri --group-add video \
  -v "$LIB":/v20/lib906:ro -v "$R/data/w858_hblt":/probe:ro \
  strata-gfx906:0.2.9-101 bash -lc '
set -u
export LD_LIBRARY_PATH=/opt/rocm/lib:${LD_LIBRARY_PATH:-}
export HIPBLASLT_TENSILE_LIBPATH=/v20/lib906
export HIPBLASLT_LOG_LEVEL=3
cd /probe
echo "--- files ---"; ls /v20/lib906
for p in probe3 probe2 probe_algos; do
  if [ -x ./$p ]; then
    echo "===== $p ====="
    timeout 120 ./$p 2>&1 | tail -14
  fi
done
' 2>&1
echo "=== probe final end $(date -u +%FT%TZ) ==="
} >> "$LOG" 2>&1
sed -n "/=== probe final start/,\$p" "$LOG" | tail -50
