set +e
D=/home/albus/strata166/gfx029
echo "===== [1] docker/build.sh ====="
sed -n '1,80p' "$D/docker/build.sh"
echo
echo "===== [2] docker/Dockerfile 的 FLAVOR 分派 ====="
grep -nE "FLAVOR|^ARG|^FROM|rocm|hip|BASE_IMAGE" "$D/docker/Dockerfile" | head -30
echo
echo "===== [3] docs/AMD_HIP.md 的关键命令 ====="
grep -nE "docker build|--build-arg|FLAVOR|ROCM|gfx906|docker run" "$D/docs/AMD_HIP.md" | head -30
echo
echo "===== [4] 谁打了 strata-gfx906 标签（本机历史脚本） ====="
grep -rln "strata-gfx906" /home/albus/strata166 --include=*.sh --include=*.py 2>/dev/null | head -10
echo "--- 直接搜 -t strata-gfx906"
grep -rn "t strata-gfx906" /home/albus/strata166 --include=*.sh 2>/dev/null | head -6
echo
echo "===== [5] 本地可用的 ROCm 基础镜像 ====="
docker images | grep -iE "rocm|ubuntu" | head -6
