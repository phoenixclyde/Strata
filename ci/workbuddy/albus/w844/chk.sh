set +e
echo "=== 容器 ==="
docker ps --format '{{.Names}} {{.Status}}' | head -5
echo "=== 构建目录 ==="
ls -l /home/albus/strata166/gfx029-build 2>/dev/null | head -5
echo "=== 日志 ==="
tail -5 /home/albus/strata166/data/w844_build.log 2>/dev/null
