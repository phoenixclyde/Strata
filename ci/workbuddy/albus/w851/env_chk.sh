set +e
echo "===== 生产 env（决定 tuner 要不要带同样变量） ====="
docker inspect strata166-407 --format '{{range .Config.Env}}{{println .}}{{end}}' | grep -E "HSA|ROCBLAS|STRATA" | head -20
