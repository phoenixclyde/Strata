set +e
L=/data/strata-huihui-ud-iq4_xs.log
echo "===== [1] 不认/弃用告警（最后一次启动之后） ====="
docker exec strata166-407 bash -lc "grep -anE 'unknown|unrecognis|unrecogniz|ignoring|deprecat|not supported|invalid option' $L | tail -10"
echo "===== [2] 最后一次启动的 arch 横幅 ====="
docker exec strata166-407 bash -lc "grep -anE 'MI50-class|exact speed switches|rounding recipe|engine 0\.1\.55|strata 0\.1\.55' $L | tail -8"
echo "===== [3] 本次落产那次启动的边界（session is up） ====="
docker exec strata166-407 bash -lc "grep -an 'session is up' $L | tail -3"
echo "===== [4] serve 侧对新引擎有没有报错 ====="
docker logs --tail 200 strata166-407 2>&1 | grep -aiE "traceback|error|warning|unexpected" | tail -6
echo "===== [5] serve 0.2.8 vs 引擎 0.1.55：serve 用到的引擎行前缀是否都出现过 ====="
docker exec strata166-407 bash -lc "grep -c 'BCOK' $L; grep -c 'arch note' $L"
