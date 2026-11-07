set +e
cd /home/albus/strata166/gfx906
echo "=== quantize_q8_0_scaled 的 HIP 分支 ==="
grep -rn -B3 -A18 "quantize_q8_0_scaled" src/kernels/cuda/quantize_act.cu 2>/dev/null | head -60
echo
echo "=== moe_hit_grouped_s2 等 #3264 提到的其它项是否存在 ==="
for k in quantize_q8_0_scaled moe_hit_grouped_s2 s2_expert_grouped; do
  printf '%-26s %s\n' "$k" "$(grep -rn "$k" src include 2>/dev/null | wc -l)"
done
