set +e
C=strata166-407
D=/home/albus/strata166/gfx029
echo "===== [1] gfx906 上 hipBLASLt 有没有内核 ====="
docker exec "$C" bash -lc 'ls /opt/rocm/lib/hipblaslt/library 2>/dev/null | head -8; echo "-- gfx906 命中:"; ls /opt/rocm/lib/hipblaslt/library 2>/dev/null | grep -c gfx906; echo "-- rocblas gfx906 目录:"; ls /opt/rocm/lib/rocblas/library 2>/dev/null | grep gfx906 | head -4'
echo
echo "===== [2] 引擎里 hipBLASLt / rocBLAS 的分派 ====="
grep -rn "hipblaslt\|hipblasLt" "$D/src" "$D/include" 2>/dev/null | grep -v "^Binary" | head -12
echo "--- rocBLAS 分派:"
grep -rn "rocblas_\|rocblas.h" "$D/src" "$D/include" 2>/dev/null | head -8
echo
echo "===== [3] STRATA_ROCBLAS_TUNING 是什么、怎么用 ====="
grep -rn "STRATA_ROCBLAS_TUNING" "$D/src" "$D/include" "$D/docs" 2>/dev/null | head -8
echo
echo "===== [4] gfx906 与 hipBLASLt 的门控（源码证据） ====="
grep -rn "hipblaslt" "$D/CMakeLists.txt" "$D/cmake" 2>/dev/null | head -10
grep -rn "STRATA_HIP_GFX906" "$D/src/prefill/gemm.cu" 2>/dev/null | head -6
echo
echo "===== [5] 我们的 rocBLAS 表文件 ====="
docker exec "$C" bash -lc 'ls -l /data/gfx906-rocblas-5.5.0.txt 2>/dev/null; head -4 /data/gfx906-rocblas-5.5.0.txt 2>/dev/null; wc -l /data/gfx906-rocblas-5.5.0.txt 2>/dev/null'
