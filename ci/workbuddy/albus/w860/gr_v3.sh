#!/bin/bash
T=/home/albus/strata166/gfx029
echo "=== STRATA_GR_V3 在源码里的全部出现 ==="
grep -rn "STRATA_GR_V3" $T/src | head -12
echo
echo "=== v3 段落的注释（fused_gr.cu 718-760）==="
sed -n '716,762p' $T/src/kernels/cuda/fused_gr.cu
