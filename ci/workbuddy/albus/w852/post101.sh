set +e
C=strata166-407
echo "===== [1] 当前生产 ====="
docker inspect "$C" --format 'image={{.Config.Image}} id={{slice .Id 0 12}} started={{.State.StartedAt}} restarts={{.RestartCount}} status={{.State.Status}}'
python3 -c "import json;d=json.load(open('/home/albus/strata166/data/strata-huihui-ud-iq4_xs.json'));print('  exe=',d['exe']);print('  table=',d['env'].get('STRATA_ROCBLAS_TUNING'));print('  env_n=',len(d['env']),' args_n=',len(d['args']))"
echo "===== [2] ROCm / serve / 组件 / terminal ====="
docker exec "$C" bash -lc 'echo -n "  rocm: "; cat /opt/rocm/.info/version; echo -n "  serve md5: "; md5sum /src/serve/server.py | cut -c1-32; echo -n "  engine: "; ls /opt/strata/components/engine/; echo -n "  terminal: "; /opt/strata/terminal/bin/strata --version 2>&1 | head -1'
echo "===== [3] 服务面 + 遥测 ====="
curl -s --max-time 6 http://127.0.0.1:8090/health | head -c 120; echo
curl -s --max-time 6 http://127.0.0.1:8090/metrics | python3 -c "import sys,json;d=json.load(sys.stdin);e=d['engine'];h=d['hardware'];print('  slots=%d vram_free=%d pcie=%s'%(e['expert_slots'],e['vram_free_mib'],e.get('pcie_frac')));print('  gpu_pcie_gen=%s width=%s rx_mb=%s'%(h.get('gpu_pcie_gen'),h.get('gpu_pcie_width'),h.get('gpu_pcie_rx_mb')))"
echo -n "  UI: "; curl -s -o /dev/null -w '%{http_code} %{size_download}B\n' --max-time 8 http://127.0.0.1:8090/
echo "  strata status（TERMINAL）:"
docker exec "$C" /usr/local/bin/strata status 2>&1 | head -6 | sed 's/^/    /'
echo "===== [4] 门禁 / tip ====="
bash /home/albus/strata166/tmp/verify_patches.sh 2>&1 | grep -E "img=|GATE"
bash /home/albus/strata166/tmp/verify_tip.sh 2>&1 | tail -2
echo "===== [5] 容器谱系 ====="
docker ps -a --filter "name=strata166-407" --format '  {{.Names}}  {{.Status}}  {{.Image}}' | head -6
