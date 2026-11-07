#!/bin/bash
cd /home/albus/strata166/pr/strata-fork || exit 1
A=origin/gfx906/0.2.9-mi50
B=origin/gfx906/0.2.8-mi50
echo "=== commits on local HEAD..origin/gfx906-0.2.8-mi50 (cc8a0711) ==="
git log --oneline 642de24f.."$B" | head -20
echo
echo "=== aef9d256 (published 0.2.9 MI50 tip) vs HEAD: the two files ==="
git diff --stat "$A" HEAD
echo
echo "=== what A has that HEAD lacks: qsa_select.cu ==="
git diff HEAD "$A" -- src/kernels/cuda/qsa_select.cu | head -60
echo
echo "=== what A has that HEAD lacks: generate.cpp ==="
git diff HEAD "$A" -- src/program/generate.cpp | head -60
