#!/bin/bash
# W863 · 把工作树对齐到已发布的 MI50 支线顶端（origin/gfx906/0.2.9-mi50 = aef9d256），
# 保留 W863 的 R 表改动，然后提交并推送，使「我们在支线顶端」在本地和 GitHub 上同时成立。
set -u
R=/home/albus/strata166/pr/strata-fork
cd "$R" || exit 1
echo "=== before ==="
git rev-parse --abbrev-ref HEAD; git rev-parse --short HEAD
git status --porcelain
echo
echo "=== keep a copy of the patched kernel (checkout must not lose it) ==="
cp -f src/kernels/cuda/native_mmvq.cu /tmp/w863_native_mmvq.cu.keep
md5sum /tmp/w863_native_mmvq.cu.keep
echo
echo "=== move the local branch to the published tip (aef9d256), carrying the patch ==="
git checkout -B gfx906/0.2.9-mi50 origin/gfx906/0.2.9-mi50 2>&1 | tail -5
echo
echo "=== diff vs aef9d256 (must be ONLY native_mmvq.cu) ==="
git status --porcelain
git diff --stat
echo
echo "=== confirm the kernel patch survived ==="
grep -c "kWaveRows\|wave_rows_env" src/kernels/cuda/native_mmvq.cu
echo
echo "=== branch picture now ==="
git branch -vv | head -6
