#!/bin/bash
# W839-10 读 generate.cpp 的架构默认接线段
S=/home/albus/strata166/src028
echo "=== generate.cpp 3360-3420 ==="
sed -n '3360,3420p' $S/src/program/generate.cpp
echo
echo "=== 该段里是否提到 gfx / hip / amd ==="
sed -n '3340,3440p' $S/src/program/generate.cpp | grep -niE 'gfx|hip|amd|arch_default|nv_default' | head -12
