#!/bin/bash
set -u
W=/home/albus/strata166/work/rebase-trial
cd $W || exit 1

echo "=== 1) 全树残留冲突标记 ==="
git diff --check 2>&1 | head -5
grep -rIl "^<<<<<<< \|^>>>>>>> " --include=*.cpp --include=*.hpp --include=*.cu --include=*.cuh --include=*.h --include=*.py --include=*.txt . 2>/dev/null | head -5
echo "(空 = 无残留)"

echo
echo "=== 2) gfx906 关键特性是否还在 ==="
for k in STRATA_GFX906_TUNED gfx906_tuned_env STRATA_HIP_GFX906 STRATA_SELECT_SIMT strata-spec STRATA_CKPT_MOVE_PARK STRATA_MMVQ_WAVE_ROWS STRATA_GDN_PP STRATA_HC_Q8 STRATA_ATTN_QUERY_SWIZZLE; do
  printf "%-28s %s\n" "$k" "$(grep -rl "$k" --include=*.cpp --include=*.hpp --include=*.cu --include=*.cuh --include=*.h --include=*.txt . 2>/dev/null | wc -l)"
done

echo
echo "=== 3) 关键文件是否存在 ==="
for f in include/strata/core/arch_defaults.hpp src/core/arch_defaults.cpp src/kernels/cuda/qsa_select.cu src/program/generate.cpp src/prefill/mmq_kq_lib.cu include/strata/platform/hip_compat/strata_hip.h; do
  [ -f "$f" ] && echo "  OK  $f" || echo "  MISSING  $f"
done

echo
echo "=== 4) 版本与提交数 ==="
grep -m1 "project(strata VERSION" CMakeLists.txt
echo "commits on top of upstream: $(git rev-list --count upstream/main..HEAD)"
echo "upstream tip: $(git log -1 --format='%h %ad' --date=short upstream/main)"

echo
echo "=== 5) arch_defaults.hpp 两个声明都在 ==="
grep -n "gfx906_tuned_env\|gfx12_prefill_share_default" include/strata/core/arch_defaults.hpp | head -5

echo
echo "=== 6) 我们的 trace 打点与 spec 覆盖 ==="
grep -c 'tr("previous commit joined")\|tr("kv ensured")\|STRATA_MTP_ROOM_MIN\|spec_override' src/program/generate.cpp

echo
echo "=== 7) 与 pre-rebase 的差异规模（应只有上游 708 条带来的变化） ==="
git diff --shortstat pre-rebase/gfx906-mi50 HEAD 2>/dev/null
