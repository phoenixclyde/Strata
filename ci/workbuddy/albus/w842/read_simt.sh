set +e
cd /home/albus/strata166/gfx906
echo "=== qsa_select.cu 2240-2300（HIP 分支解析 0/1/2） ==="
sed -n '2240,2300p' src/kernels/cuda/qsa_select.cu
echo
echo "=== 该文件里 simt 取值的完整解析（含 =2 的实际使用点） ==="
grep -n "simt2\|block_scores_simt2" src/kernels/cuda/qsa_select.cu | head -20
