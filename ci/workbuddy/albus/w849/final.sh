set +e
echo "===== 磁盘 ====="; df -h / | tail -1
echo "===== 镜像清单（新增候选） ====="; docker images strata-gfx906 --format '{{.Tag}}  {{.Size}}  {{.CreatedSince}}' | head -6
echo "===== 生产未动确认 ====="
docker inspect strata166-407 --format 'image={{.Config.Image}} id={{slice .Id 0 12}} started={{.State.StartedAt}} restarts={{.RestartCount}}'
curl -s --max-time 5 http://127.0.0.1:8090/health | head -c 100; echo
bash /home/albus/strata166/tmp/verify_tip.sh 2>&1 | tail -3
