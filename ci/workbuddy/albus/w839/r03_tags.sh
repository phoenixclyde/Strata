#!/bin/bash
# W839-03 分支侧：查 v0.2.8 tag 可得性 + 测试文件真实路径 + 提交结构
W=/home/albus/strata166/gfx906
cd $W || exit 1
echo "=== 分支里测试文件的路径 ==="
git ls-files | grep -i arch_defaults
echo
echo "=== 本地 tag ==="
git tag | grep -E '0\.2\.[0-9]' | tail -6 || echo "no tags"
echo "=== 远端 tag（我们 fork 是否带上游 tag） ==="
timeout 40 git ls-remote --tags origin 'v0.2.*' 2>&1 | tail -8
echo
echo "=== 提交结构（相对基线的 9 个） ==="
git log --oneline -9
echo
echo "=== 与上游 main 的单文件差异面 ==="
git diff --stat ghup/main..HEAD 2>/dev/null | tail -12 || echo "(ghup not fetched in this clone)"
