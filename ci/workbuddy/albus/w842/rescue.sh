set +e
DATA=/home/albus/strata166/data
CFG=$DATA/strata-huihui-ud-iq4_xs.json
LOG=$DATA/strata-huihui-ud-iq4_xs.log
echo "=== 先恢复生产配置（n3 / 6 env） ==="
cp /tmp/w842_prod.json "$CFG" && echo cfg-restored
python3 -c "import json;d=json.load(open('$CFG'));print('exe=',d['exe'],'env_n=',len(d.get('env') or {}))"
docker restart strata166-407 >/dev/null 2>&1
for i in $(seq 1 420); do curl -s --max-time 2 http://127.0.0.1:8090/health >/dev/null 2>&1 && { echo "health ok in ${i}s"; break; }; sleep 1; done
echo
echo "=== 崩溃现场：docker logs 尾部 ==="
docker logs --tail 25 strata166-407 2>&1 | tail -25
echo
echo "=== 引擎日志：最后一次启动的报错 ==="
tail -60 "$LOG" | grep -aiE "error|fail|abort|cannot|out of|no such|terminate|assert" | tail -15
echo "--- 引擎日志最后 12 行 ---"
tail -12 "$LOG"
