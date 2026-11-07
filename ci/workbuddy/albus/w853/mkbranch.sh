#!/bin/bash
# W853: 给 hipBLASLt 单开分支 + 独立 worktree（生产树 gfx029 不受影响）
set -u
S=/home/albus/strata166/gfx029
W=/home/albus/strata166/gfx-hblt
BR=gfx906/hipblaslt-vega20
BASE=gfx906/0.2.9-mi50   # = aef9d25，与生产同源

cd "$S" || exit 1
echo "== 1 现状"
echo "  当前分支: $(git rev-parse --abbrev-ref HEAD) @ $(git rev-parse --short HEAD)"
echo "  BASE = $BASE @ $(git rev-parse --short $BASE)"

echo "== 2 建 worktree + 分支"
if [ -d "$W" ]; then echo "  worktree 已存在: $W"; else
  git worktree add -B "$BR" "$W" "$BASE" 2>&1 | tail -3
fi
echo "  新 worktree: $(git -C "$W" rev-parse --abbrev-ref HEAD) @ $(git -C "$W" rev-parse --short HEAD)"

echo "== 3 把方案文件搬进去（从生产树未跟踪的 docs/）"
mkdir -p "$W/docs"
cp -a "$S/docs/hipblaslt-gfx906" "$W/docs/"
rm -rf "$S/docs/hipblaslt-gfx906"
rmdir "$S/docs" 2>/dev/null
echo "  生产树 docs 是否已清空: $(ls "$S/docs" 2>/dev/null | wc -l) 项"

echo "== 4 提交"
cd "$W" || exit 1
git add docs/hipblaslt-gfx906
git -c user.name=albus -c user.email=albus@localhost commit -q -F - <<'MSG'
gfx906: open a branch for the hipBLASLt (vega20) backend attempt

hipBLASLt has no gfx906 kernels: upstream leaves gfx906 out of
cmake/tensilelite_supported_architectures.cmake, ships no vega20 logic,
and the asm generator emits gfx90a+ directives (.amdhsa_accum_offset).
Both ROCm 7.14 and 10.1 answer hipblasLtMatmulAlgoGetHeuristic with
status=3 (NOT_SUPPORTED) and algos=0.

That is a "rewrite a backend" problem, not a "tune a table" problem, so it
does not belong on the production branch.  This branch carries only the
plan, the two probes and the one-line whitelist patch, so the question
"can it be built at all" gets an answer from a measurement instead of an
argument.

  docs/hipblaslt-gfx906/PLAN.md          pass/fail criteria (P0/P1/P2) + 10 steps
  docs/hipblaslt-gfx906/probe_hblt.cpp   does hipBLASLt give *any* algo here
  docs/hipblaslt-gfx906/probe_tensilelite.sh  P0: can TensileLite emit+assemble one gfx906 kernel
  docs/hipblaslt-gfx906/patches/0001-...      whitelist gfx906 (reversible, own commit)

Production (gfx906/0.2.9-mi50) is untouched and keeps running the rocBLAS
path: ROCm 10.1 + the 84-row gfx906-rocblas-5.7.0.txt table.
MSG
echo "  commit = $(git rev-parse --short HEAD)"
git log --oneline -2 | sed 's/^/    /'
echo "== 5 push"
timeout 300 git push -u origin "$BR" 2>&1 | tail -5
echo "== 6 复核"
git branch -vv | grep hblt | sed 's/^/  /'
git status --porcelain | head -3
echo "== 7 生产树是否干净"
echo "  gfx029 branch=$(git -C "$S" rev-parse --abbrev-ref HEAD) dirty=$(git -C "$S" status --porcelain | wc -l)"
