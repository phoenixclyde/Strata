set +e
D=/home/albus/strata166/gfx029
cd "$D" || exit 1
echo "===== [1] 旧分支 vs 新分支的完整 diff（13 行） ====="
git diff gfx906/0.2.8-mi50 gfx906/0.2.9-mi50
echo
echo "===== [2] 逐文件对比（旧分支 vs 新分支） ====="
for f in CMakeLists.txt include/strata/core/arch_defaults.hpp include/strata/kernels/gfx_arch.hpp \
         include/strata/platform/hip_compat/strata_hip.h serve/telemetry.py serve/web/app.css serve/web/app.js \
         src/core/arch_defaults.cpp src/core/arch_defaults_test.cpp src/kernels/cuda/qsa_decode_attn.cu \
         src/kernels/cuda/qsa_select.cu src/program/generate.cpp; do
  a=$(git show gfx906/0.2.8-mi50:"$f" 2>/dev/null | md5sum | cut -c1-8)
  b=$(git show gfx906/0.2.9-mi50:"$f" 2>/dev/null | md5sum | cut -c1-8)
  c=$(md5sum "$D/$f" 2>/dev/null | cut -c1-8)
  [ "$a" = "$b" ] && s=same || s=DIFF
  [ "$b" = "$c" ] && t=ok || t="WORKTREE!=HEAD"
  printf '  %-44s old=%s new=%s wt=%s  %s %s\n' "$f" "$a" "$b" "$c" "$s" "$t"
done
echo
echo "===== [3] 旧工作副本（gfx906）里还有没有未提交改动 ====="
git -C /home/albus/strata166/gfx906 status --porcelain | head -10
echo -n "  行数 = "; git -C /home/albus/strata166/gfx906 status --porcelain | wc -l
