#!/bin/bash
set -u
W=~/strata166/work/r66
cd $W || exit 1

echo "=== 应用 p1 ==="
patch -p1 < /tmp/r66_p1.patch 2>&1 | tail -3
echo "=== 应用 p2 ==="
patch -p1 < /tmp/r66_p2.patch 2>&1 | tail -3

echo
echo "=== p3 再 dry-run（p1 已在前）==="
patch -p1 --dry-run < /tmp/r66_p3.patch 2>&1 | head -8

echo
echo "=== p3 的 hunk #1 原文（要看它期望什么上下文）==="
sed -n '/^@@/,/^@@/p' /tmp/r66_p3.patch | head -40

echo
echo "=== 我方 prefill.cpp 对应区域（1450-1480）==="
sed -n '1450,1480p' src/prefill/prefill.cpp
