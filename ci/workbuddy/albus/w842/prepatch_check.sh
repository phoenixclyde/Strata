set +e
cd /home/albus/strata166/gfx906
echo "=== [1] simt2 kernel 体内是否有 wave32 假设 ==="
sed -n '606,700p' src/kernels/cuda/qsa_select.cu | grep -n -E "shfl|& ?31|>> ?5|warpSize|__syncwarp|dpp|bpermute" | head
echo "(空 = 无 warp32 假设)"
echo
echo "=== [2] block_scores_tail_kernel 是否对 HIP 可用 ==="
grep -n "block_scores_tail_kernel" src/kernels/cuda/qsa_select.cu | head
echo
echo "=== [3] 是否有 #if !defined(__HIPCC__) 包住 simt2 / tail ==="
awk 'NR>=596 && NR<=700 && /#if|#else|#endif/ {printf "%d: %s\n", NR, $0}' src/kernels/cuda/qsa_select.cu | head -12
echo
echo "=== [4] 锚点唯一性 ==="
grep -c -F "return v != nullptr && v[0] == '1';" src/kernels/cuda/qsa_select.cu
grep -c -F "if (simt_on && !(wmma_on && sel_gfx12_device()))" src/kernels/cuda/qsa_select.cu
