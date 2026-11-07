#!/bin/bash
S=/home/albus/strata166
echo "=== A. build-port2 缓存来源 ==="
grep -m2 -E "CMAKE_HOME_DIRECTORY|CMAKE_CACHEFILE_DIR" $S/build-port2/CMakeCache.txt
grep -m2 "STRATA_MMQ_TQ_OVERLAY" $S/build-port2/CMakeCache.txt
echo
echo "=== B. overlay 生成器是否带 W1037 的修（port-all vs k10）==="
md5sum $S/pr/port-all/cmake/strata_ggml_tq_overlay.cmake $S/pr/k10/cmake/strata_ggml_tq_overlay.cmake 2>/dev/null
diff -q $S/pr/port-all/cmake/strata_ggml_tq_overlay.cmake $S/pr/k10/cmake/strata_ggml_tq_overlay.cmake && echo SAME || echo DIFFER
grep -n "write_back_mma\|signature\|probe" $S/pr/port-all/cmake/strata_ggml_tq_overlay.cmake | head -8
echo
echo "=== C. build-port2 里 ninja 是否被改过（RERUN_CMAKE 是否 phony）==="
grep -c "RERUN_CMAKE" $S/build-port2/build.ninja
grep -m2 -n "RERUN_CMAKE" $S/build-port2/build.ninja
echo
echo "=== D. port-all 的 /llama.cpp 当前挂载源（build.ninja 里引用的路径）==="
grep -o "/llama.cpp/ggml/src/ggml-cuda/mmq.cuh" $S/build-port2/build.ninja | head -1
echo
echo "=== E. 现有 build-port2 产物 ==="
ls -l $S/build-port2/strata 2>/dev/null
md5sum $S/build-port2/strata 2>/dev/null
