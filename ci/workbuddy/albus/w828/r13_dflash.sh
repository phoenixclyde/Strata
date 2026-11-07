echo "--- 0.1.53 build had dflash2? ---"
find /home/albus/strata166/src0271/build-0271 -name 'dflash2*' 2>/dev/null | head
echo "--- hip_compat stream macros ---"
grep -n -E 'StreamPriority|CreateWithPriority|StreamNonBlocking|DeviceGetStream' /home/albus/strata166/src028/include/strata/platform/hip_compat/strata_hip.h
echo "--- where DFLASH2 is set in CMake (0.2.8) ---"
grep -n -B3 -A6 'STRATA_HAVE_DFLASH2' /home/albus/strata166/src028/CMakeLists.txt | head -40
echo "--- where DFLASH2 is set in CMake (0.1.53) ---"
grep -n -B3 -A6 'STRATA_HAVE_DFLASH2' /home/albus/strata166/src0271/CMakeLists.txt | head -40
echo "--- dflash2.cpp new? diff api ---"
grep -n 'cudaStreamCreateWithPriority\|cudaDeviceGetStreamPriorityRange' /home/albus/strata166/src0271/src/core/dflash2.cpp | head
