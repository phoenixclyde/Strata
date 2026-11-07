#!/bin/bash
set -u
S=~/strata166/pr/strata-fork
cd $S

echo "########## A. 708 条按关键词分类（计数） ##########"
R="HEAD..upstream/main"
for kw in "hip\|HIP" "rocm\|ROCm" "gfx" "amd\|AMD" "mi50\|MI50" "crash\|segfault\|hang\|deadlock\|fault" "regression\|revert" \
          "quant\|iq2\|iq3\|iq4\|q4_k\|q5\|q6\|q8" "mmq\|mmvq\|gemv" "moe\|expert" "attn\|attention\|qsa\|fa\b" \
          "decode" "prefill\|prompt" "cache" "kv" "gdn\|ssm" "spec\|draft\|mtp" "ple" "split" "dflash"; do
  n=$(git log --oneline $R --grep="$kw" -i 2>/dev/null | wc -l)
  printf "  %-34s %4d\n" "$kw" "$n"
done

echo
echo "########## B. 提及 HIP / gfx / AMD / MI50 的全部提交 ##########"
git log --format="%h %ad %s" --date=short $R --grep="hip\|rocm\|gfx\|amd\|mi50" -i 2>/dev/null | cut -c1-155

echo
echo "########## C. 崩溃 / 挂死 / 回归类（正确性优先） ##########"
git log --format="%h %ad %s" --date=short $R --grep="crash\|segfault\|hang\|deadlock\|fault\|regression\|revert\|corrupt" -i 2>/dev/null | cut -c1-155 | head -30

echo
echo "########## D. 触及我们改过的 10 个文件的提交数 ##########"
MB=$(git merge-base HEAD upstream/main)
for f in src/program/generate.cpp CMakeLists.txt src/prefill/fused_gr.cu src/core/arch_defaults_test.cpp \
         src/core/arch_defaults.cpp include/strata/core/arch_defaults.hpp src/kernels/cuda/native_mmvq.cu \
         src/kernels/cuda/qsa_select.cu App/app.js Serve/telemetry.py; do
  n=$(git log --oneline HEAD..upstream/main -- "$f" 2>/dev/null | wc -l)
  [ "$n" -gt 0 ] && printf "  %-52s %4d\n" "$f" "$n"
done
