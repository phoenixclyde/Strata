set +e
D=/home/albus/strata166/gfx029
echo "===== [1] 0.1.55 里 --ple-io 还在不在、取值是什么 ====="
grep -rn "ple-io\|ple_io\|PLE_IO" "$D/src" "$D/include" 2>/dev/null | head -10
echo
echo "===== [2] 文档怎么说 ====="
grep -rn "ple-io" "$D/docs" 2>/dev/null | head -6
echo
echo "===== [3] 当前运行有没有 PLE 相关日志/告警 ====="
docker exec strata166-407 bash -lc 'grep -aiE "ple|mlock" /data/strata-huihui-ud-iq4_xs.log | tail -8'
echo
echo "===== [4] 容器 ulimit / 内存现状（X1 与 P147 的前提） ====="
docker exec strata166-407 bash -lc 'ulimit -l; free -g | head -2'
echo "--- 宿主: free -g"; free -g | head -2
