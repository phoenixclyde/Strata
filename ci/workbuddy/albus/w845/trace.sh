set +e
L=/data/strata-huihui-ud-iq4_xs.log
echo "===== [1] 三次引擎启动的完整命令行（带时间戳） ====="
docker exec strata166-407 bash -lc "grep -an 'engine started' $L | tail -4"
echo
echo "===== [2] 三次 session is up 的行号（再列一次） ====="
docker exec strata166-407 bash -lc "grep -an 'session is up' $L | tail -4"
echo
echo "===== [3] 76600-77260 之间的 serve 事件（exit / restart / 切换） ====="
docker exec strata166-407 bash -lc "sed -n '76600,77260p' $L | grep -anE 'expert profile saved|engine started|engine 0\.1\.5|session is up|exiting|restart|reload' | head -20"
echo
echo "===== [4] 落产脚本的输出（它做了什么） ====="
tail -25 /home/albus/strata166/data/w844_deploy_192952.txt 2>/dev/null
echo
echo "===== [5] 现在有没有残留脚本在改配置 ====="
pgrep -af "w844_|ab.sh|deploy.sh|restore" | head -6
ls -l --time-style=+%m-%d_%H:%M:%S /home/albus/strata166/data/strata-huihui-ud-iq4_xs.json
