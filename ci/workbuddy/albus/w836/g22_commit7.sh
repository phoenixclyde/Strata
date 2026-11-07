#!/bin/bash
# W836: commit 7 -- the HIP compat layer entry points (W830-COMPAT), then push
set -e
F=/home/albus/strata166/pr/strata-fork
S=/home/albus/strata166/src028
cd $F || exit 1
git checkout gfx906/0.2.8-mi50 2>&1 | tail -1

cp -a "$S/include/strata/platform/hip_compat/strata_hip.h" include/strata/platform/hip_compat/strata_hip.h
echo "--- diff to be committed ---"
git diff -U2 -- include/strata/platform/hip_compat/strata_hip.h | grep -E '^[+-][^+-]' | head -12

git add include/strata/platform/hip_compat/strata_hip.h
git commit -q -F - <<'MSG'
gfx906: name the two stream-priority entry points in the HIP compat layer

Upstream 0.1.54's src/core/dflash2.cpp calls cudaStreamCreateWithPriority and
cudaDeviceGetStreamPriorityRange directly.  On the wave32 HIP backend those
arrive through hipify, which this tree does not run for the gfx906 target: the
hand-written macro table in strata_hip.h has to name them, and did not, so the
gfx906 build failed on exactly those two symbols.

Adds only the two #define lines, next to the existing stream entries.  No
behaviour change on any card that already had them.
MSG

echo
echo "=== push ==="
git push origin gfx906/0.2.8-mi50 2>&1 | tail -4
echo
echo "=== branch now ==="
git log --oneline ghup/main..HEAD
echo
git diff --stat ghup/main..HEAD | tail -8
