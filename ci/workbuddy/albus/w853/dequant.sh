set +e
D=/home/albus/strata166/gfx029
echo "===== [1] 相位计时点：dequant / wait copy 在哪打的 ====="
grep -rn "\"dequant\"\|dequant" "$D/src/prefill/prefill.cpp" 2>/dev/null | head -12
echo
echo "===== [2] wait copy 的计时点 ====="
grep -rn "wait copy" "$D/src/prefill/prefill.cpp" "$D/src"/*.cpp 2>/dev/null | head -8
echo
echo "===== [3] gemm gate/up 与 down 的计时点 ====="
grep -rn "gemm gate/up\|gemm down" "$D/src/prefill/prefill.cpp" 2>/dev/null | head -6
echo
echo "===== [4] 反量化 kernel 有哪些（Q4_K → FP16） ====="
ls "$D/src/kernels/cuda/" 2>/dev/null | grep -iE "dequant|mmq|quant" | head -12
grep -rn "dequant" "$D/src/prefill/kernels.cu" 2>/dev/null | head -10
