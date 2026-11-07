#!/bin/bash
# inner: reverse-engineered config -> Tensile --cpu-only --build-only (gfx906 VALU)
set -u
export LD_LIBRARY_PATH=/opt/rocm/lib:${LD_LIBRARY_PATH:-}
TL=/src/projects/hipblaslt/tensilelite
export PYTHONPATH=/g858/pylib:/g858/rocisa-install:$TL

echo "--- 1. fix TensileLibLogicToYaml ---"
python3 /v20/fix_lib2yaml.py $TL/Tensile/TensileLibLogicToYaml.py

echo "--- 2. reverse-engineer solutions 0/1/2 ---"
mkdir -p /v20/cfg
cd /v20
for i in 0 1 2; do
  timeout 120 python3 $TL/Tensile/bin/TensileLibLogicToYaml -i /v20/logic/vega20_Cijk_Ailk_Bjlk_HHS_BH.yaml -d $i -o /v20/cfg/idx$i --skipMI 2>&1 | tail -1
done
ls -l /v20/cfg/ 2>/dev/null | head -6

echo "--- 3. patch configs ---"
for i in 0 1 2; do
  cp /v20/cfg/idx$i /tmp/cfg_idx$i.yaml
  python3 /v20/patch_cfg.py /tmp/cfg_idx$i.yaml
done
echo "--- patched idx0 ---"
sed -n "1,40p" /tmp/cfg_idx0.yaml

echo "--- 3b. fix MAC_F16_HPA (gfx906 f16 HPA 的唯一 MAC 组件) ---"
python3 /v20/fix_mac.py $TL/Tensile/Components/MAC_F16_HPA.py

echo "--- 3c. enable v_dot2_f32_f16 on gfx906 ---"
python3 /v20/fix_dot2.py $TL/Tensile/SolutionStructs/Solution.py

echo "--- 4. generate ---"
rm -rf /out/gen14
mkdir -p /out/gen14 /out/work
cd /out/work
nice -n 19 timeout 900 python3 $TL/Tensile/bin/Tensile --cpu-only --build-only --gpu-targets=gfx906 --library-format=yaml /tmp/cfg_idx0.yaml /out/gen14 2>&1 | grep -viE "rejecting solution" | tail -20

echo "--- 5. artifacts ---"
find /out/gen14 -name "*.hsaco" -o -name "TensileLibrary*" -o -name "*.s" 2>/dev/null | head -8
