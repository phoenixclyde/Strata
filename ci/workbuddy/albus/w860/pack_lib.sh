#!/bin/bash
set -u
SRC=/home/albus/strata166/data/w859_hblt/gen15/1_BenchmarkProblems/Cijk_Ailk_Bjlk_HHS_BH_UserArgs_00/00_Final/caches/d95bdc892bfc/source/library/gfx906
D=/home/albus/strata166/data/w860_vega20/lib906
mkdir -p $D
cp -f "$SRC/Kernels.so-000-gfx906-xnack-.hsaco" "$D/Kernels.so-000-gfx906.hsaco"
cp -f "$SRC/TensileLibrary.yaml" "$D/TensileLibrary_lazy_gfx906.yaml"
cp -f "$SRC/TensileLibrary_gfx906.co" "$D/TensileLibrary_gfx906.co" 2>/dev/null || true
ls -l $D
echo "--- head of the yaml ---"
head -14 "$D/TensileLibrary_lazy_gfx906.yaml"
