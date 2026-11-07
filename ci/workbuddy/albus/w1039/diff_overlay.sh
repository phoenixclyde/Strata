#!/bin/bash
S=/home/albus/strata166
echo "=== diff overlay 生成器（port-all vs k10）==="
diff -u $S/pr/port-all/cmake/strata_ggml_tq_overlay.cmake $S/pr/k10/cmake/strata_ggml_tq_overlay.cmake
echo "RC=$?"
