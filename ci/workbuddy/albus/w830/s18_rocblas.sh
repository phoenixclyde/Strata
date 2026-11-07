S=/home/albus/strata166/src028
echo "=== rocBLAS-related strings the engine can print ==="
grep -n "rocblas" "$S/src/prefill/gemm.cu" | head -20
echo
echo "=== the tuning-table load path ==="
grep -rn "STRATA_ROCBLAS_TUNING" "$S/src" "$S/include" | head -10
echo
echo "=== what it says when it loads / fails to load ==="
grep -rn "ROCBLAS_TUNING" -A3 -B3 "$S/src/prefill/gemm.cu" | head -40
