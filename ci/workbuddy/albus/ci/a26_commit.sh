#!/usr/bin/env bash
# Commit the parameter-combination probes and record what they changed.
set -eu
R=/home/albus/strata166/pr/strata-fork
cd "$R"

echo "=== 1. what changed ==="
git status --porcelain --untracked-files=all

echo
echo "=== 2. no stray .bak under src/ (gate rule) ==="
find src include -name '*.bak*' 2>/dev/null | head -5 || true

echo
echo "=== 3. config-face + script syntax gate ==="
python3 ci/gate.py --repo . --source-only --allow-missing-build 2>&1 | tail -6
for f in ci/*.sh ci/strata-ci; do [ -f "$f" ] && bash -n "$f" && echo "ok   $f"; done
python3 -m py_compile ci/*.py && echo "ok   ci/*.py"

echo
echo "=== 4. commit ==="
git add ci/probe/rs_probe.cpp ci/probe/rs_probe_run.sh \
        ci/probe/launch_probe.cpp ci/probe/launch_probe_run.sh \
        docs/DOWNSTREAM.md 2>/dev/null || true
git -c user.name=phoenixclyde -c user.email=phoenixclyde@users.noreply.github.com commit -q -F - <<'MSG'
probe: R x S interaction and launch granularity -- two conclusions reversed

R and S were only ever swept one at a time. Both change parallelism, but R merges the output
axis while S cuts the reduction axis, so their effects on locality run in opposite directions
and a single-variable sweep cannot see the interaction. rs_probe sweeps both and deliberately
gives several (R,S) pairs the same block count, which is what makes the comparison meaningful.

What came out:

  * expert shape -- rows with equal block count agree within 2% (32 blocks: R1S4 553, R2S8 554,
    R4S16 564 GB/s). R and S are interchangeable there. Optimum is 32-64 blocks (0.5-1.1/CU).
  * HC down -- with arithmetic the optimum moves left: fma is flat at 520-548 for S=1..4 and
    falls to 358-403 at S=16. Production runs S=16 (Q8_KC 640, Q8_NKC 16), i.e. the right edge.
  * no strong interaction in the arithmetic modes, which rules out grid shape as the cause of
    the HC gap -- a negative result that is worth as much as a positive one.

launch_probe holds total bytes fixed and varies only how many launches it takes to read them:
rep=1 (production's shape, one small kernel per layer) 260 GB/s, rep=128 (fully batched) 458.
Batching is worth 1.76x, but production's 97 GB/s is still 2.7x below the rep=1 probe, so the
launch cost is not the whole story.

This also corrects two earlier numbers of ours:

  * R32's "5.6x is the arithmetic" is withdrawn. That collapse came from the probe filling a
    8 KB LDS tile once per block -- up to 5.7x the data volume. With the tile in registers the
    same conditions hold 528-548 GB/s, so arithmetic costs about 18%, not 5.6x.
  * R35's dp4a "+73..117%" is withdrawn. That compared fma over a 32-way-conflicted LDS tile
    against dp4a over a different stride: two variables at once. Both in registers: 548 -> 673,
    i.e. +15..23%, which caps at ~1.0-1.4% of wall clock and is below the 8% A/B threshold.
MSG
git --no-pager log --oneline -1

echo
echo "=== 5. tag + push ==="
git -c user.name=phoenixclyde -c user.email=phoenixclyde@users.noreply.github.com tag -a mi50-0.2.9-r10 \
  -m 'MI50 drop r10: R x S interaction probe and launch-granularity probe. Two earlier conclusions reversed (R32 arithmetic share, R35 dp4a). Engine binary unchanged; probes only.' HEAD
git push origin gfx906/mi50 2>&1 | tail -2
git push origin mi50-0.2.9-r10 2>&1 | tail -2

echo
echo "=== 6. final ==="
git rev-parse --short HEAD
git describe --exact-match --tags HEAD
git status --porcelain --untracked-files=all | wc -l
