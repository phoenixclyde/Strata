echo "=== the configure options that produced 0.1.54 (from build-028w's cache) ==="
grep -E "^(STRATA_[A-Z0-9_]+|CMAKE_BUILD_TYPE|CMAKE_HIP_ARCHITECTURES|CMAKE_CXX_COMPILER|CMAKE_HIP_COMPILER|CMAKE_GENERATOR|GGML_[A-Z_]+):" \
  /home/albus/strata166/src028/build-028w/CMakeCache.txt 2>/dev/null | grep -v "INTERNAL" | head -50
echo
echo "=== was rocBLAS found in that configure? ==="
grep -iE "rocblas|hipblas" /home/albus/strata166/src028/build-028w/CMakeCache.txt 2>/dev/null | head -8
grep -iE "rocblas|ROCBLAS_AVAILABLE" /home/albus/strata166/src028/build-028w.log 2>/dev/null | head -6
echo
echo "=== r02_cfg.sh (current content) ==="
cat /home/albus/strata166/tmp/r02_cfg.sh 2>/dev/null | head -40
