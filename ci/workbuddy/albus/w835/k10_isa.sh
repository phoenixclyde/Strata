#!/bin/bash
# W835: settle the gfx906 instruction-truth question at the assembler level + production snapshot
echo "=== A. find llvm-mc that knows gfx906 ==="
for c in llvm-mc llvm-mc-18 llvm-mc-19 /opt/rocm/llvm/bin/llvm-mc /opt/rocm/llvm/bin/llvm-mc-*; do
  command -v $c >/dev/null 2>&1 && { echo "found: $(command -v $c)"; MC=$(command -v $c); break; }
  [ -x "$c" ] && { echo "found: $c"; MC=$c; break; }
done
[ -z "$MC" ] && MC=$(ls /opt/rocm*/llvm/bin/llvm-mc 2>/dev/null | head -1)
echo "MC=$MC"
echo
echo "=== B. assemble the disputed instructions for gfx906 ==="
if [ -n "$MC" ]; then
  for ins in "v_dot2_f32_f16 v0, v1, v2, v3" \
             "v_dot4_i32_i8 v0, v1, v2, v3" \
             "v_dot8_i32_i4 v0, v1, v2, v3" \
             "v_dot4c_i32_i8 v0, v1, v2" \
             "v_mfma_f32_16x16x16_f16 v0, v1, v2, v3" \
             "v_mov_b32_dpp v0, v1 quad_perm:[1,0,3,2] row_mask:0xf bank_mask:0xf"; do
    out=$(echo "$ins" | $MC -triple=amdgcn-amd-amdhsa -mcpu=gfx906 -show-encoding 2>&1)
    if echo "$out" | grep -q "encoding:"; then
      echo "  [OK ] $ins"
    else
      echo "  [NO ] $ins   <- $(echo "$out" | head -1 | cut -c1-90)"
    fi
  done
fi
echo
echo "=== C. what does the shipped Strata binary actually contain? ==="
B=/home/albus/strata166/data/bin/strata-0.1.54n2
for op in v_dot2_f32_f16 v_dot4_i32_i8 v_mfma v_mov_b32_dpp ds_bpermute; do
  n=$(grep -ac "$op" "$B" 2>/dev/null || echo 0)
  echo "  $op in binary: $n"
done
echo "  (note: instruction names may not appear as strings in a compiled ELF - use roc-objdump instead)"
ls /opt/rocm*/llvm/bin/roc-objdump /opt/rocm*/bin/roc-objdump 2>/dev/null | head -2
echo
echo "=== D. production snapshot ==="
date +%H:%M:%S
docker inspect strata166-407 --format 'img={{.Config.Image}} status={{.State.Status}}' 2>/dev/null
curl -s --max-time 4 http://127.0.0.1:8090/health | head -c 120; echo
python3 /home/albus/strata166/tmp/state_q.py --no-probe 2>&1 | sed -n '2,12p'
