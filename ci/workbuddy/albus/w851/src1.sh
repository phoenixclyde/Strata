set +e
D=/home/albus/strata166/gfx029
echo "===== [1] rocBLAS 表的生成器（tuner）在树里吗 =====" 
ls -l "$D/tools" | head -30
echo "--- 名字里带 tune/rocblas 的:"
find "$D" -maxdepth 3 -iname "*tune*" -not -path "*/.git/*" 2>/dev/null | head -20
echo
echo "===== [2] 表格式与解析代码 ====="
grep -rn "STRATA_ROCBLAS_TUNING_V1\|STRATA_RocBLAS_TUNING_V1" "$D/src" "$D/include" "$D/tools" "$D/packaging" 2>/dev/null | head -10
echo
echo "===== [3] gemm.cu 里 rocBLAS 路径的关键段（版本检查 + 查表） ====="
grep -n "rocblas\|RocBlas\|tuning" "$D/src/prefill/gemm.cu" 2>/dev/null | head -40
