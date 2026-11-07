#!/bin/bash
# W839-01 现场勘察：生产量化 + 分支状态 + 构建可行性
D=/home/albus/strata166
W=$D/gfx906
date +%H:%M:%S
echo "=== 生产容器 ==="
docker ps --format '{{.Names}} | {{.Status}}' | grep -E 'strata166|w8' || echo NONE
docker inspect strata166-407 --format 'img={{.Config.Image}}' 2>/dev/null
curl -s --max-time 4 http://127.0.0.1:8090/health | head -c 90; echo
echo "=== 生产量化 ==="
python3 $D/tmp/state_q.py --no-probe 2>&1 | sed -n '4,12p'

echo "=== 分支工作副本 ==="
cd $W || exit 1
git rev-parse --short HEAD
git log --oneline -3
echo "-- status --"
git status --porcelain | head -6
echo "-- remotes --"
git remote -v | grep -E 'origin|upstream|ghup' | head -6
echo "-- tags/branches --"
git tag | head -8
git branch -a | head -10

echo "=== 构建目录 ==="
ls -d $W/build* 2>/dev/null || echo "no build dir in worktree"
ls -d $D/src028/build* 2>/dev/null | head
for b in $W/build* $D/src028/build-028r; do
  [ -d "$b" ] && { echo "[$b] ninja=$([ -f $b/build.ninja ] && echo yes || echo no)"; }
done

echo "=== src028 与分支的源码差异（只列文件数） ==="
n=0
for f in CMakeLists.txt src/core/arch_defaults.cpp include/strata/core/arch_defaults.hpp tests/unit/arch_defaults_test.cpp src/serve/../serve/telemetry.py serve/web/app.css serve/web/app.js src/kernels/cuda/qsa_decode_attn.cu include/strata/platform/hip_compat/strata_hip.h; do
  [ -f "$W/$f" ] || { echo "  MISSING-in-branch $f"; continue; }
  if cmp -s "$W/$f" "$D/src028/$f"; then echo "  same  $f"; else echo "  DIFF  $f"; n=$((n+1)); fi
done
echo "DIFF count=$n"

echo "=== 构建镜像 ==="
docker images --format '{{.Repository}}:{{.Tag}}' | grep -E 'gfx906|strata' | head -6
