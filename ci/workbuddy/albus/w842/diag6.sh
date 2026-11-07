set +e
echo "=== 容器崩溃原因（最近 3 次退出） ==="
docker logs --tail 200 strata166-407 2>&1 | grep -aE "Traceback|Error|error|Killed|out of memory|VRAM|Address already|CUDA|abort|Segmentation" | tail -20
echo
echo "=== 最近一次正常启动的尾巴 ==="
docker logs --tail 12 strata166-407 2>&1
echo
echo "=== 引擎日志里 n3 arm 时段的报错 ==="
grep -aiE "error|fail|cannot|no room|not enough|non-finite" /home/albus/strata166/data/strata-huihui-ud-iq4_xs.log | tail -12
