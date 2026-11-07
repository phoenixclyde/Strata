#!/bin/bash
set -u
R=/home/albus/strata166/pr/strata-fork
cd "$R" || exit 1
echo "=== abort the rebase ==="
git rebase --abort 2>&1 | tail -3
echo
echo "=== state ==="
git rev-parse --abbrev-ref HEAD; git rev-parse --short HEAD
git status --porcelain --untracked-files=no | head -5
echo
echo "=== back to the MI50 branch (force, the patch is committed in 78fa2a72) ==="
git checkout -f gfx906/0.2.9-mi50 2>&1 | tail -3
echo
echo "=== verify ==="
git rev-parse --abbrev-ref HEAD; git rev-parse --short HEAD
git status --porcelain | head -5
echo -n "kernel patch present (kWaveRows+wave_rows_env): "; grep -c "kWaveRows\|wave_rows_env" src/kernels/cuda/native_mmvq.cu
echo -n "tree vs HEAD diff: "; git diff --stat HEAD | tail -1
echo
echo "=== history of main, to see why the rebase conflicted ==="
git log --oneline --graph --decorate -8 origin/main
echo "--- merge-base main/upstream ---"
git merge-base origin/main upstream/main | cut -c1-12
git rev-parse --short origin/main upstream/main
echo "--- is e8ca9afd an ancestor of upstream/main? ---"
git merge-base --is-ancestor e8ca9afd upstream/main && echo YES || echo NO
echo "--- is e8ca9afd an ancestor of origin/main? ---"
git merge-base --is-ancestor e8ca9afd origin/main && echo YES || echo NO
