set +e
echo "===== 生产状态 ====="
docker inspect strata166-407 --format 'image={{.Config.Image}} id={{slice .Id 0 12}} started={{.State.StartedAt}} restarts={{.RestartCount}}'
curl -s --max-time 6 http://127.0.0.1:8090/metrics | python3 -c "import sys,json;d=json.load(sys.stdin);e=d['engine'];print('  slots=%d vram_free=%d pcie=%s'%(e['expert_slots'],e['vram_free_mib'],e.get('pcie_frac')))"
echo "===== 残留 arm 容器（应只有 3 个 Exited） ====="
docker ps -a --filter "name=strata166-407" --format '  {{.Names}}  {{.Status}}  {{.Image}}'
echo "===== 磁盘 ====="; df -h / | tail -1
echo "===== tip ====="
bash /home/albus/strata166/tmp/verify_tip.sh 2>&1 | tail -4
