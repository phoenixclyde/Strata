#!/bin/bash
# W839-17 提交并推送分支
set -u
W=/home/albus/strata166/gfx906
cd $W || exit 1
echo "=== 改动面 ==="
git diff --stat | tail -3
echo
git add -A src/program/generate.cpp
git -c user.name=phoenixclyde -c user.email=phoenixclyde@users.noreply.github.com \
  commit -q -m "gfx906: actually call apply_arch_defaults on this build

The per-card table is applied from a block guarded by \`#if defined(STRATA_USE_HIP)\`.
This build defines only STRATA_HIP_GFX906, and W717/P23 measured that a global
STRATA_USE_HIP switches CUDA-only paths elsewhere, so it stays scoped to dflash2.cpp.
Effect: arch_defaults.cpp was referenced by no translation unit, was therefore not
linked into the engine at all (nm: no apply_arch_defaults, no banner strings), and the
gfx906 entry added in 642de24 could not run.

Add the same call under STRATA_HIP_GFX906: same contract as the other builds - every
visible card is the same architecture and a switch the user already set is kept.
STRATA_GFX906_DEFAULTS=0 still turns the table off." || { echo "commit failed"; exit 2; }
git log --oneline -1
echo "=== push ==="
git push origin gfx906/0.2.8-mi50 2>&1 | tail -3
echo "=== 远端 head ==="
git rev-parse --short HEAD
