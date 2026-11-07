set +e
S=/home/albus/strata166/gfx906
D=/home/albus/strata166/gfx029
echo "=== restore_cmake.py 用法 ==="
head -20 /home/albus/strata166/tmp/restore_cmake.py
echo
echo "=== 复制 10 个补丁文件 ==="
for f in src/kernels/cuda/qsa_decode_attn.cu src/kernels/cuda/qsa_select.cu serve/telemetry.py serve/web/app.css serve/web/app.js \
         include/strata/platform/hip_compat/strata_hip.h include/strata/kernels/gfx_arch.hpp \
         include/strata/core/arch_defaults.hpp src/core/arch_defaults.cpp src/core/arch_defaults_test.cpp; do
  if [ -f "$S/$f" ]; then cp -a "$S/$f" "$D/$f" && echo "  copied $f"; else echo "  MISSING $f"; fi
done
echo
echo "=== generate.cpp 锚点补丁 ==="
python3 /home/albus/strata166/patches/apply_w839_generate.py "$D/src/program/generate.cpp" 2>&1 | tail -3
grep -c "W839 local" "$D/src/program/generate.cpp"
echo
echo "=== CMakeLists：先只查标记，不自动 patch ==="
grep -c "W793" "$D/CMakeLists.txt"; grep -c "W776 local" "$D/CMakeLists.txt"
echo
echo "=== 与旧树对比这 10 个文件 ==="
for f in src/kernels/cuda/qsa_decode_attn.cu src/kernels/cuda/qsa_select.cu serve/telemetry.py serve/web/app.css serve/web/app.js \
         include/strata/platform/hip_compat/strata_hip.h include/strata/kernels/gfx_arch.hpp \
         include/strata/core/arch_defaults.hpp src/core/arch_defaults.cpp src/core/arch_defaults_test.cpp src/program/generate.cpp; do
  a=$(md5sum "$S/$f" 2>/dev/null | cut -d' ' -f1); b=$(md5sum "$D/$f" 2>/dev/null | cut -d' ' -f1)
  [ "$a" = "$b" ] && echo "  same  $f" || echo "  DIFF  $f  $a vs $b"
done
