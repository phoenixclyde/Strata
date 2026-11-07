#!/bin/bash
M=/opt/rocm/llvm/bin/llvm-mc
probe() {
  arch=$1; ins=$2
  printf '%-34s @ %-8s -> ' "$ins" "$arch"
  out=$(echo "$ins" | $M -triple=amdgcn-amd-amdhsa -mcpu=$arch -show-encoding 2>&1)
  if echo "$out" | grep -qiE 'error|invalid|not supported'; then
    echo "REJECTED: $(echo "$out" | head -1 | cut -c1-90)"
  else
    echo "OK: $(echo "$out" | tail -2 | head -1 | cut -c1-70)"
  fi
}
for a in gfx906 gfx90a; do
  probe $a "v_dot2_f32_f16 v0, v1, v2, v3"
  probe $a "v_mad_mix_f32 v0, v1, v2, s0"
  probe $a "v_fma_mix_f32 v0, v1, v2, s0"
  echo
done
