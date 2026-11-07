set +e
echo "=== $(date +%H:%M:%S) 容器 ==="
docker ps --format '{{.Names}} {{.Status}}' | grep w844 || echo "not running"
echo "=== 日志尾 ==="
tail -4 /home/albus/strata166/data/w844_build.log 2>/dev/null
echo "=== 产物 ==="
ls -l /home/albus/strata166/gfx029-build/strata /home/albus/strata166/gfx029-build/strata-0.1.55g 2>/dev/null || echo "no binary yet"
echo "=== 对象数 ==="
find /home/albus/strata166/gfx029-build/CMakeFiles -name "*.o" 2>/dev/null | wc -l
