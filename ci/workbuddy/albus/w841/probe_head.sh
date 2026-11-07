set +e
cd /home/albus/strata166/gfx906
echo "=== multi_block_head_ops / argmax_rows_wanted 定义 ==="
grep -rn -A12 "bool multi_block_head_ops" src/kernels/cuda/verify_kernels.cu | head -30
echo "----"
grep -rn -A12 "bool argmax_rows_wanted" src/kernels/cuda/verify_kernels.cu | head -30
echo
echo "=== 是否已按 __HIPCC__ 关掉 ==="
grep -rn "__HIPCC__" src/kernels/cuda/verify_kernels.cu | head -12
