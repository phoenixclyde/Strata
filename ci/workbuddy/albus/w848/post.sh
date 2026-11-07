set +e
C=strata166-407
L=$(ls -t /home/albus/strata166/data/w848_swap_*.txt | head -1)
echo "===== [1] 切换日志的关键段 ====="
sed -n '/-- 自证 --/,$p' "$L" | head -34
echo
echo "===== [2] terminal 在容器里能真用吗（关键） ====="
echo -n "  strata --version : "; docker exec "$C" /usr/local/bin/strata --version 2>&1 | head -1
echo "  strata status:"; docker exec "$C" /usr/local/bin/strata status 2>&1 | head -10 | sed 's/^/    /'
echo "  strata monitor --once（前 8 行）:"; docker exec "$C" /usr/local/bin/strata monitor --once 2>&1 | head -8 | sed 's/^/    /'
echo
echo "===== [3] 指纹 ====="
docker inspect "$C" --format 'image={{.Config.Image}} id={{slice .Id 0 12}} started={{.State.StartedAt}} restarts={{.RestartCount}}'
docker image inspect strata-gfx906:0.2.9t --format 'img=0.2.9t id={{.Id}} size={{.Size}}'
echo "--- 容器谱系:"; docker ps -a --filter "name=strata166-407" --format '  {{.Names}}  {{.Status}}  {{.Image}}'
echo
echo "===== [4] 门禁 + 服务面 ====="
bash /home/albus/strata166/tmp/verify_patches.sh 2>&1 | grep -E "img=|GATE"
curl -s --max-time 6 http://127.0.0.1:8090/health | head -c 150; echo
curl -s --max-time 6 http://127.0.0.1:8090/metrics | python3 -c "import sys,json;d=json.load(sys.stdin);e=d['engine'];print('  slots=%d vram_free=%d pcie=%s'%(e['expert_slots'],e['vram_free_mib'],e.get('pcie_frac')))"
