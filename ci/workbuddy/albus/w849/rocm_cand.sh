set +e
C=/home/albus/strata166/img029r
TAG=strata-gfx906:0.2.9r1
rm -rf "$C"; mkdir -p "$C"
cat > "$C/Dockerfile" <<'DOCKER'
# W849/X15 候选：把 /opt/rocm 换成 ROCm 10.1.0 / HIP 7.16（来自本机 routek-base:gfx906-rocm101-hip716 的 gfx906 构建）
# 目的只是**静态验证**：现有 0.1.55g 能否在新 soname 下加载、rocBLAS 是否带 gfx906 内核。不碰生产。
FROM routek-base:gfx906-rocm101-hip716-torch215-tv030-df1 AS rocm101
FROM strata-gfx906:0.2.9t2
COPY --from=rocm101 /opt/rocm /opt/rocm
RUN set -e; \
    echo "--- 新 /opt/rocm 版本:"; cat /opt/rocm/.info/version 2>/dev/null || ls /opt/rocm | head -3; \
    echo "--- rocblas 内核架构:"; ls /opt/rocm/lib/rocblas/library | grep -c gfx906; \
    echo "--- soname:"; ls /opt/rocm/lib/libamdhip64.so.* /opt/rocm/lib/librocblas.so.5.* /opt/rocm/lib/libhipblaslt.so.* 2>/dev/null | head -6
DOCKER
echo "===== [1] 构建（复制 5 GB userland，几分钟） ====="
docker build -t "$TAG" "$C" 2>&1 | grep -E "新 /opt/rocm|rocblas 内核|soname|libamdhip|librocblas|libhipblaslt|DONE|ERROR|naming" | tail -12
docker image inspect "$TAG" --format '  id={{.Id}} size={{.Size}}' 2>/dev/null
echo
echo "===== [2] 静态验证：现有二进制在新 ROCm 下能否解析依赖 ====="
docker run --rm --entrypoint bash "$TAG" -lc '
  echo -n "  ldd 缺失项数: "; ldd /data/bin/strata-0.1.55g 2>&1 | grep -c "not found"
  echo "  解析到的关键库:"
  ldd /data/bin/strata-0.1.55g 2>/dev/null | grep -E "rocblas|amdhip|hipblaslt" | sed "s/^/    /"
  echo -n "  --version: "; /data/bin/strata-0.1.55g --version 2>&1 | head -1
  echo -n "  rocblas 版本文件: "; ls /opt/rocm/lib/librocblas.so.5.* 2>/dev/null | head -1
  echo -n "  hipcc: "; hipcc --version 2>/dev/null | grep -i "HIP version" | head -1
'
