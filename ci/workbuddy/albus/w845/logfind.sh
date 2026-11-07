set +e
echo "===== 找引擎日志 ====="
ls -lt --time-style=+%m-%d_%H:%M /home/albus/strata166/data/*.log 2>/dev/null | head -5
ls -lt --time-style=+%m-%d_%H:%M /home/albus/strata166/data/logs/ 2>/dev/null | head -5
echo "--- 容器内 /data 下 *.log:"
docker exec strata166-407 bash -lc "ls -lt --time-style=+%m-%d_%H:%M /data/*.log /data/logs/* 2>/dev/null | head -5"
