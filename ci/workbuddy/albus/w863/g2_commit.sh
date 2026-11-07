#!/bin/bash
set -u
R=/home/albus/strata166/pr/strata-fork
cd "$R" || exit 1
git add src/kernels/cuda/native_mmvq.cu
git -c user.name="phoenixclyde" -c user.email="phoenixclyde@users.noreply.github.com" commit -q -F - <<'MSG'
gfx906: rows-per-wavefront table for the Q8_0 wave kernel (single-request decode GEMV)

A single-request decode runs a speculative verify window, so native_mmvq is called with
ncols > 1.  Per weight block the kernel then issues NCOLS times the activation loads and
dp4a work, and wave_launch_n hardcoded R = 1: one row per wavefront, none of that work
shared.  Measured on the shapes that matter at ncols 6, R = 2 gives 1.6-1.8x and R = 4
gives 1.9x on qkv/gate/q, and the whole layer goes 613.6 -> 385.4 us.

The table is measured, not a formula: 9 shapes x ncols 1..8 x R in {1,2,4} on the real
kernel with this build's flags (216 cells).  A cell keeps R > 1 only when it beat R = 1
by >= 3 % on that shape at that column count; ncols = 1 stays at R = 1 (a formula that
picked R = 4 there cost 0.982x on the whole layer, out 6144->2560 alone 10.2 %), and an
unmeasured shape keeps R = 1.

STRATA_MMVQ_WAVE_ROWS overrides it at run time (1 = the old behaviour, 2 or 4 = that many
rows everywhere), which is also the A/B arm.  The per-row reduction order does not change,
so the result is bitwise identical: 9 shapes at ncols 1 and 6, diff = 0.

Production A/B (same image, same binary, only that env differs, interleaved T B T B,
3 x 480-token greedy decodes per arm): 48.6 vs 46.8 tok/s, +4.0 %.
MSG
echo "=== commit ==="
git log --oneline -2
echo
echo "=== push to our MI50 branch ==="
timeout 180 git push origin gfx906/0.2.9-mi50 2>&1 | tail -6
echo
echo "=== remote tip now ==="
git ls-remote --heads origin gfx906/0.2.9-mi50
