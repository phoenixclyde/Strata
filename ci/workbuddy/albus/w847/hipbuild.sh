set +e
T=/home/albus/strata166/gfx029
echo "===== build_hip_linux.sh（打包段） ====="
grep -nE "BUILD.json|stage_tuning|package_engine|collect_libs|--arch|hipblaslt|ROCM" "$T/packaging/build_hip_linux.sh" | head -30
echo
echo "===== 该脚本 90-180 行 ====="
sed -n '90,180p' "$T/packaging/build_hip_linux.sh"
