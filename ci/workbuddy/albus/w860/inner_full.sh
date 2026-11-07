#!/bin/bash
# inner: 完整 Tensile（复用 build-only 的 cache），产出带 mapping 的库
set -u
export LD_LIBRARY_PATH=/opt/rocm/lib:${LD_LIBRARY_PATH:-}
TL=/src/projects/hipblaslt/tensilelite
export PYTHONPATH=/g858/pylib:/g858/rocisa-install:$TL
export HSA_OVERRIDE_GFX_VERSION=9.0.6

python3 /v20/fix_dot2.py $TL/Tensile/SolutionStructs/Solution.py
python3 /v20/fix_mac.py $TL/Tensile/Components/MAC_F16_HPA.py

echo "--- full Tensile with --use-cache ---"
cd /out/work
nice -n 19 timeout 900 python3 $TL/Tensile/bin/Tensile --use-cache \
  --gpu-targets=gfx906 --library-format=yaml /v20/gfx906_f16_hand.yaml /out/gen16 2>&1 \
  | grep -viE 'W860-REJECT|rejecting solution' | tail -24

echo "--- library tree ---"
find /out/gen16 -maxdepth 3 -name '*.dat' -o -maxdepth 3 -name '*.hsaco' -o -maxdepth 3 -name 'TensileLibrary*' 2>/dev/null | head -12
