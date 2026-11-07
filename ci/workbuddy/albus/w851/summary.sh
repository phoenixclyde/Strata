set +e
echo "===== rocBLAS tuning summary（析构时打印，含 tuned_launches / fallbacks） ====="
docker exec strata166-407 bash -lc "grep -an 'rocBLAS tuning summary' /data/strata-huihui-ud-iq4_xs.log | tail -10"
echo
echo "===== 对照：有没有别的 f16_inplace 相关日志 ====="
docker exec strata166-407 bash -lc "grep -anE 'f16_inplace|f16 io|tuned_launches' /data/strata-huihui-ud-iq4_xs.log | tail -6"
echo
echo "===== 最近一次启动之后有没有 prompt 请求（看 read 行） ====="
docker exec strata166-407 bash -lc "grep -ac 'read in [0-9]* ms' /data/strata-huihui-ud-iq4_xs.log"
