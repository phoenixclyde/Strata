D=/home/albus/strata166/build024/patches
S27=/home/albus/strata166/src0271
S28=/home/albus/strata166/src028
echo "=== targets named inside the patch scripts ==="
for f in patch_mmq_tile_j.py patch_gr_tilev.py patch_final_ckpt.py patch_gfx906_attn_swizzle.py patch_gfx906_rocblas.py; do
  echo "[$f]"
  grep -nE "mmq|fused_gr|\.cu|\.cuh|\.cpp|CMakeLists|argv|sys\.argv|path\s*=" "$D/$f" | grep -vE "^\s*#" | head -8
done
echo
echo "=== third_party/llama.cpp present? ==="
for d in "$S27" "$S28"; do
  printf '  %-46s ' "$d/third_party/llama.cpp"
  [ -d "$d/third_party/llama.cpp" ] && echo "dir OK" || echo "MISSING"
  ls -la "$d/third_party/llama.cpp/ggml/src/ggml-cuda/mmq.cuh" 2>/dev/null | awk '{print "     mmq.cuh", $5, $6, $7, $8}'
done
echo
echo "=== the W795 / W788 log strings in the shipped binary ==="
B=/home/albus/strata166/data/bin/strata-0.1.54n
for s in "MMQ tile: type" "GR tilev" "TILEV" "W795" "w795_j_cap"; do
  n=$(grep -a -c -F -- "$s" "$B" 2>/dev/null || echo 0)
  echo "  [$s] bin=$n"
done
