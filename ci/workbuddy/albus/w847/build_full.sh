set -eu
T=/home/albus/strata166/gfx029
P=/home/albus/strata166/pkgs
C=/home/albus/strata166/img029
TAG=strata-gfx906:0.2.9
PKG=0.1.55-linux-x86_64-hip-gfx906

echo "===== [1] 组装上下文（0.2.9 全树 + 组件包） ====="
rm -rf "$C"; mkdir -p "$C"
cp -a "$T" "$C/src"
rm -rf "$C/src/.git" "$C/src/build-029g"
find "$C/src" -name __pycache__ -type d -prune -exec rm -rf {} + 2>/dev/null || true
find "$C/src" -name '*.pyc' -delete 2>/dev/null || true
mkdir -p "$C/engine"
cp -a "$P/components/engine/$PKG" "$C/engine/"
cat > "$C/Dockerfile" <<DOCKER
# W847: 完整 0.2.9 镜像 —— /src 换成 v0.2.9 全树（含 12 个本地补丁），
# 并把 0.1.55 的 hip/gfx906 引擎组件按上游 packaging 流程装进 /opt/strata/components/engine。
# 不再保留 0.2.4/0.2.8 时代的 /src/src、/src/include 混搭。
FROM strata-gfx906:0.2.8p2
COPY src/ /src/
COPY engine/$PKG /opt/strata/components/engine/$PKG
DOCKER
du -sh "$C/src" "$C/engine" | sed 's/^/  /'
echo "  树内文件数: $(find "$C/src" -type f | wc -l)   组件文件数: $(find "$C/engine" -type f | wc -l)"

echo "===== [2] 构建 ====="
docker build -t "$TAG" "$C" 2>&1 | tail -6
docker images "$TAG" --format '  {{.Repository}}:{{.Tag}} {{.Size}} {{.Id}}'

echo "===== [3] 镜像自证：/src 是否真的是 0.2.9 全树 ====="
docker run --rm --entrypoint bash "$TAG" -lc '
  echo -n "  0.2.9 独有文件 gdn_probe.hpp: "; ls /src/include/strata/prefill/gdn_probe.hpp 2>/dev/null || echo MISSING
  echo -n "  0.2.9 独有文件 gdn_wmma12.inc: "; ls /src/src/prefill/gdn_wmma12.inc 2>/dev/null || echo MISSING
  echo -n "  0.2.9 独有文件 replica_profile.py: "; ls /src/strata_control/replica_profile.py 2>/dev/null || echo MISSING
  echo -n "  /src 文件数: "; find /src -type f | wc -l
  echo -n "  serve/server.py md5: "; md5sum /src/serve/server.py | cut -d" " -f1
  echo -n "  telemetry.py  md5: "; md5sum /src/serve/telemetry.py | cut -d" " -f1
  echo -n "  /opt/strata/components/engine: "; ls /opt/strata/components/engine/
  echo -n "  组件 verify: "; python3 /src/packaging/package_engine.py --verify /opt/strata/components/engine/'$PKG' 2>&1 | tail -1
'
echo "FULL-IMG-OK"
