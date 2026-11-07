set +e
C=/home/albus/strata166/img029t2
rm -rf "$C"; mkdir -p "$C"
cat > "$C/Dockerfile" <<'DOCKER'
# W848b: 镜像里的 PORT 默认 8080，而生产在 8090 ⇒ wrapper 的 STRATA_URL 指错端口（strata status 报 URLError）
# 把默认端口对齐生产，`docker exec <c> strata status/monitor` 才能直接用
FROM strata-gfx906:0.2.9t
ENV PORT=8090
DOCKER
docker build -t strata-gfx906:0.2.9t2 "$C" 2>&1 | tail -3
docker image inspect strata-gfx906:0.2.9t2 --format '  id={{.Id}} size={{.Size}}'
docker run --rm --entrypoint bash strata-gfx906:0.2.9t2 -lc 'echo -n "  PORT="; echo $PORT; echo -n "  wrapper url: "; STRATA_URL=""; echo "http://127.0.0.1:${PORT:-8080}"'
