set +e
C=strata166-407
D=/home/albus/strata166/data
echo "===== [1] 切换日志里的 serve 自证段 ====="
grep -aA4 "serve 版本自证" $D/w846_swap_200244.txt | head -8
echo
echo "===== [2] 容器 / 镜像现状 ====="
docker inspect "$C" --format 'image={{.Config.Image}} id={{slice .Id 0 12}} started={{.State.StartedAt}} restarts={{.RestartCount}} status={{.State.Status}}'
docker images strata-gfx906 --format '{{.Repository}}:{{.Tag}} {{.Size}} {{.Id}}' | head -3
echo "--- 旧容器（回滚件）:"
docker ps -a --filter "name=strata166-407" --format '  {{.Names}} {{.Status}} {{.Image}}'
echo
echo "===== [3] HTTP 表面 ====="
printf '  /health: '; curl -s --max-time 5 http://127.0.0.1:8090/health | head -c 200; echo
printf '  / (UI)  : '; curl -s -o /dev/null -w '%{http_code} %{size_download}B\n' --max-time 8 http://127.0.0.1:8090/
printf '  /metrics keys(engine): '; curl -s --max-time 6 http://127.0.0.1:8090/metrics | python3 -c "import sys,json;d=json.load(sys.stdin);print(sorted(d['engine'].keys())[:18])"
printf '  pcie 字段: '; curl -s --max-time 6 http://127.0.0.1:8090/metrics | python3 -c "
import sys,json;e=json.load(sys.stdin)['engine']
print({k:v for k,v in e.items() if 'pcie' in k.lower() or 'fru' in k.lower() or 'mem' in k.lower()})"
echo
echo "===== [4] 0.2.9 的 serve 是否真的在跑（PS + 版本行） ====="
docker exec "$C" bash -lc "ps -o pid,cmd -C python3 | head -3; md5sum /src/serve/server.py; grep -c COALESCE_PREFILL /src/serve/server.py; grep -c PAR_COUNTERS /src/serve/server.py"
echo
echo "===== [5] serve 侧有没有新报错 ====="
docker logs --tail 60 "$C" 2>&1 | grep -aiE "traceback|error|exception|warning" | tail -6
echo
echo "===== [6] 门禁（再跑一遍） ====="
bash /home/albus/strata166/tmp/verify_patches.sh 2>&1 | tail -3
