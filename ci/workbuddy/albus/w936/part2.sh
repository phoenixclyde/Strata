#!/bin/bash
set -u
cd ~/strata166/pr/strata-fork || exit 1
echo "=== ds4_main.cpp 部分 ==="
git show e1b27d54 -- src/dsv41/ds4_main.cpp | head -80
echo
echo "=== generate.cpp 部分 ==="
git show e1b27d54 -- src/program/generate.cpp
