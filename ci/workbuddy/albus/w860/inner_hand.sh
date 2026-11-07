#!/bin/bash
# inner: hand config + force reject print -> Tensile --cpu-only --build-only
set -u
export LD_LIBRARY_PATH=/opt/rocm/lib:${LD_LIBRARY_PATH:-}
TL=/src/projects/hipblaslt/tensilelite
export PYTHONPATH=/g858/pylib:/g858/rocisa-install:$TL

echo "--- enable v_dot2_f32_f16 on gfx906 ---"
python3 /v20/fix_dot2.py $TL/Tensile/SolutionStructs/Solution.py

echo "--- force reject printing ---"
python3 /v20/fix_reject.py $TL/Tensile/BenchmarkProblems.py

echo "--- generate ---"
rm -rf /out/gen15
mkdir -p /out/gen15 /out/work
cd /out/work
nice -n 19 taskset -c 0-3 timeout 900 python3 $TL/Tensile/bin/Tensile --cpu-only --build-only --gpu-targets=gfx906 --library-format=yaml /v20/gfx906_f16_hand.yaml /out/gen15 2>&1 | grep -viE "rejecting solution \{" | tail -26

echo "--- artifacts ---"
find /out/gen15 -name "*.hsaco" -o -name "TensileLibrary*" -o -name "*.s" 2>/dev/null | head -8
