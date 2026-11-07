S=/home/albus/strata166/src028
echo "=== anchors present in 0.2.8? ==="
printf '  A include_directories/elseif : '; grep -c -F "set(_strata_gpu_include_directories \${CMAKE_CUDA_TOOLKIT_INCLUDE_DIRECTORIES})" "$S/CMakeLists.txt"
printf '  A2 elseif(STRATA_ENABLE_CUDA) : '; grep -c -F "elseif(STRATA_ENABLE_CUDA)" "$S/CMakeLists.txt"
printf '  B rocblas guard line        : '; grep -c -F "if(STRATA_ENABLE_HIP AND STRATA_ROCBLAS_AVAILABLE)" "$S/CMakeLists.txt"
printf '  C strata_engine link line   : '; grep -c -F "target_link_libraries(strata_engine PUBLIC strata_core strata_kernels strata_kernels_cpu" "$S/CMakeLists.txt"
printf '  D dflash2.cpp source line   : '; grep -c -F "src/core/dflash2.cpp" "$S/CMakeLists.txt"
echo
echo "=== the gfx906 branch head in 0.2.8 (context for A) ==="
grep -n -B2 -A6 "set(_strata_gpu_include_directories \${CMAKE_CUDA_TOOLKIT_INCLUDE_DIRECTORIES})" "$S/CMakeLists.txt" | head -24
echo
echo "=== does 0.2.8's dflash2.cpp still key on STRATA_USE_HIP? ==="
grep -n "STRATA_USE_HIP" "$S/src/core/dflash2.cpp" | head -12
echo "  (count: $(grep -c 'STRATA_USE_HIP' "$S/src/core/dflash2.cpp"))"
echo
echo "=== and the stream-priority calls we macro-patched last night ==="
grep -n "cudaDeviceGetStreamPriorityRange\|cudaStreamCreateWithPriority" "$S/src/core/dflash2.cpp" | head -6
grep -n "cudaDeviceGetStreamPriorityRange\|cudaStreamCreateWithPriority" "$S/include/strata/platform/hip_compat/strata_hip.h" | head -6
