set +e
C=/home/albus/strata166/img029r
TAG=strata-gfx906:0.2.9r1
rm -rf "$C"; mkdir -p "$C"
cat > "$C/Dockerfile" <<'DOCKER'
# W849/X15 候选镜像：/opt/rocm 整体换成 ROCm 10.1.0 / HIP 7.16（gfx906 构建，来自本机 routek-base）
# 先删旧树再拷，避免 base 的 /opt/rocm/bin 等符号链接导致 "cannot copy to non-directory"
FROM routek-base:gfx906-rocm101-hip716-torch215-tv030-df1 AS rocm101
FROM strata-gfx906:0.2.9t2
RUN rm -rf /opt/rocm /opt/rocm-*
COPY --from=rocm101 /opt/rocm /opt/rocm
DOCKER
echo "===== [1] 构建 ====="
docker build -t "$TAG" "$C" 2>&1 | tail -8
docker image inspect "$TAG" --format '  id={{.Id}} size={{.Size}}' 2>/dev/null
echo
echo "===== [2] 新 ROCm 是什么 ====="
docker run --rm --entrypoint bash "$TAG" -lc '
  echo -n "  /opt/rocm/.info/version: "; cat /opt/rocm/.info/version 2>/dev/null || echo "(无该文件)"
  echo -n "  rocblas gfx906 内核: "; ls /opt/rocm/lib/rocblas/library 2>/dev/null | grep -c gfx906
  echo -n "  rocblas soname: "; ls /opt/rocm/lib/librocblas.so.5* 2>/dev/null | head -2 | tr "\n" " "; echo
  echo -n "  hip soname: "; ls /opt/rocm/lib/libamdhip64.so.* 2>/dev/null | head -2 | tr "\n" " "; echo
  echo -n "  hipcc: "; PATH=/opt/rocm/bin:$PATH hipcc --version 2>/dev/null | grep -i "HIP version" | head -1
'
echo
echo "===== [3] 静态验证：0.1.55g 在新 ROCm 下 ====="
docker run --rm --entrypoint bash "$TAG" -lc '
  echo -n "  ldd 缺失: "; ldd /data/bin/strata-0.1.55g 2>&1 | grep -c "not found"
  ldd /data/bin/strata-0.1.55g 2>/dev/null | grep -E "rocblas|amdhip|hipblaslt" | sed "s/^/    /"
  echo -n "  --version: "; /data/bin/strata-0.1.55g --version 2>&1 | head -1
'
