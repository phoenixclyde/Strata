set +e
echo "===== 容器 ====="
docker ps -a --filter "name=strata166-407" --format '  {{.Names}}  {{.Status}}  {{.Image}}' | head -5
echo "===== health ====="
curl -s --max-time 5 http://127.0.0.1:8090/health 2>/dev/null | head -c 120; echo
echo "===== 镜像 tag ====="
docker images strata-gfx906 --format '  {{.Tag}}  {{.Id}}' | head -8
echo "===== 是否有 finalize 在跑 ====="
pgrep -af "finalize" | head -3
