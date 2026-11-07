#!/bin/bash
# W836: did the earlier (timed-out) configure actually finish? check its artifacts
B=/home/albus/strata166/gfx906-build
echo "=== A. what the earlier run produced ==="
ls -la $B 2>/dev/null | head -12
echo
echo "=== B. cfg.log tail ==="
tail -8 $B/cfg.log 2>/dev/null || echo "(no cfg.log)"
echo
echo "=== C. the two things W793/W776 must show ==="
echo "--- rocBLAS in configure output ---"
grep -nE "rocblas|ROCBLAS" $B/cfg.log 2>/dev/null | head -8 || echo "(none)"
echo "--- STRATA_ROCBLAS_AVAILABLE in cache ---"
grep -n "STRATA_ROCBLAS_AVAILABLE" $B/CMakeCache.txt 2>/dev/null | head -3 || echo "(cache not written yet)"
echo "--- STRATA_USE_HIP in build.ninja (W776) ---"
if [ -f $B/build.ninja ]; then grep -c "STRATA_USE_HIP" $B/build.ninja; else echo "(no build.ninja)"; fi
echo
echo "=== D. is a build dir of the same tree already in use elsewhere? ==="
ls -d /home/albus/strata166/src028/build-028r 2>/dev/null && echo "  src028/build-028r exists (the production build tree)"
