set +e
cd /home/albus/strata166/gfx906
echo "=== qsa_select.cu 2195-2245（HIP 分支） ==="
sed -n '2195,2245p' src/kernels/cuda/qsa_select.cu
echo
echo "=== block_scores_simt2_kernel 是否 wave32 专用（看 launch_bounds / 用法） ==="
sed -n '596,616p' src/kernels/cuda/qsa_select.cu
