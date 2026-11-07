set +e
C=/home/albus/strata166/img029
PKG=0.1.55-linux-x86_64-hip-gfx906
TAG=strata-gfx906:0.2.9
echo "===== [1] 清掉 base 层残留的 0.2.4 构建目录（让 /src 只有 0.2.9） ====="
docker run --rm --entrypoint bash strata-gfx906:0.2.8p2 -lc 'du -sh /src/build-906 2>/dev/null; ls /src/build-906 | head -3'
cat > "$C/Dockerfile" <<DOCKER
# W847: 完整 0.2.9 镜像 —— /src = v0.2.9 全树（含 12 个本地补丁），
# 0.1.55 的 hip/gfx906 引擎组件按上游 packaging 流程装进 /opt/strata/components/engine。
# 并删掉 base 层遗留的 0.2.4 构建目录，避免 /src 里混着两代产物。
FROM strata-gfx906:0.2.8p2
COPY src/ /src/
COPY engine/$PKG /opt/strata/components/engine/$PKG
RUN rm -rf /src/build-906 /src/build-028 /src/build
DOCKER
echo "===== [2] 重建 ====="
docker build -t "$TAG" "$C" 2>&1 | tail -4
docker image inspect "$TAG" --format '  id={{.Id}} size={{.Size}}'
echo "===== [3] 复核 /src 文件数与残留 ====="
docker run --rm --entrypoint bash "$TAG" -lc 'echo -n "  /src files: "; find /src -type f | wc -l; echo -n "  build-906: "; ls -d /src/build-906 2>/dev/null || echo gone; echo -n "  serve md5: "; md5sum /src/serve/server.py | cut -d" " -f1; echo -n "  component: "; ls /opt/strata/components/engine/'
