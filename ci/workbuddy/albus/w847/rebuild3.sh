set +e
C=/home/albus/strata166/img029
PKG=0.1.55-linux-x86_64-hip-gfx906
TAG=strata-gfx906:0.2.9
cat > "$C/Dockerfile" <<DOCKER
# W847: 完整 0.2.9 镜像
#   /src = v0.2.9 全树（含 12 个本地补丁），删掉 base 层遗留的 0.2.4 构建目录与编译缓存
#   /opt/strata/components/engine = 0.1.55 hip/gfx906 组件（按上游 packaging 流程打包并 --verify）
FROM strata-gfx906:0.2.8p2
COPY src/ /src/
COPY engine/$PKG /opt/strata/components/engine/$PKG
RUN set -e; \
    rm -rf /src/build-906 /src/build-028 /src/build; \
    find /src -name __pycache__ -type d -prune -exec rm -rf {} + 2>/dev/null || true; \
    find /src -name '*.bak-w*' -delete 2>/dev/null || true; \
    find /src -name '*.pyc' -delete 2>/dev/null || true
DOCKER
echo "===== 重建 ====="
docker build -t "$TAG" "$C" 2>&1 | tail -3
docker image inspect "$TAG" --format '  id={{.Id}} size={{.Size}}'
echo "===== 复核 ====="
docker run --rm --entrypoint bash "$TAG" -lc '
  echo -n "  /src files: "; find /src -type f | wc -l
  echo -n "  pycache 残留: "; find /src -name __pycache__ | wc -l
  echo -n "  .bak 残留: "; find /src -name "*.bak-w*" | wc -l
  echo -n "  serve md5: "; md5sum /src/serve/server.py | cut -d" " -f1
  echo -n "  component verify: "; python3 /src/packaging/package_engine.py --verify /opt/strata/components/engine/'$PKG' 2>&1 | tail -1
  echo -n "  engine --version (组件里的): "; /opt/strata/components/engine/'$PKG'/strata --version 2>&1 | head -1
'
