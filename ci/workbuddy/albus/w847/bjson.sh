set +e
T=/home/albus/strata166/gfx029
echo "===== [1] 谁写 BUILD.json ====="
grep -rln "BUILD.json" "$T/packaging" "$T/tools" "$T/setup.py" 2>/dev/null | head
echo "--- stage_tuning.py 头部 ====="
sed -n '1,45p' "$T/packaging/stage_tuning.py" 2>/dev/null
echo
echo "===== [2] hipblaslt_version 在哪被要求/写入 ====="
grep -rn "hipblaslt_version" "$T" --include=*.py 2>/dev/null | head -12
echo
echo "===== [3] package_engine.py 对 hip 的 BUILD.json 校验段 ====="
sed -n '180,215p' "$T/packaging/package_engine.py"
echo
echo "===== [4] docs/AMD_HIP.md 里 packaging/镜像 的步骤 ====="
grep -nE "package_engine|stage_tuning|BUILD.json|build.sh|docker build" "$T/docs/AMD_HIP.md" | head -20
