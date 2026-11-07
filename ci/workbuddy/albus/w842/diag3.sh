set +e
echo "=== 容器挂载（关键：bin 是目录挂还是文件挂） ==="
docker inspect strata166-407 --format '{{range .Mounts}}{{.Type}} {{.Source}} -> {{.Destination}} (rw={{.RW}}){{println}}{{end}}'
echo "=== 容器内能否看到 n4 ==="
docker exec strata166-407 bash -lc "ls -l /data/bin/ | head" 2>&1 | head -8
echo
echo "=== 启动器报错上下文（n4 前后 20 行） ==="
docker logs strata166-407 2>&1 | grep -n "strata-0.1.54n4" | head -3
docker logs strata166-407 2>&1 | sed -n '/strata-0.1.54n4/,+6p' | head -12
