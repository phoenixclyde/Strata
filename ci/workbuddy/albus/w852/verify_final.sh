set +e
C=strata166-407
echo "===== [1] 指纹 ====="
docker inspect "$C" --format 'image={{.Config.Image}} id={{slice .Id 0 12}} started={{.State.StartedAt}} restarts={{.RestartCount}}'
echo "===== [2] 层信息 ====="
docker exec "$C" bash -lc '
  echo -n "  rocm: "; cat /opt/rocm/.info/version
  echo -n "  rocblas: "; ls /opt/rocm/lib/librocblas.so.5.* | head -1 | sed "s#.*/librocblas.so.##"
  echo -n "  hipcc: "; hipcc --version 2>/dev/null | grep -oE "HIP version: [0-9.]+" | head -1
  echo -n "  serve: "; md5sum /src/serve/server.py | cut -c1-16
  echo -n "  engine: "; ls /opt/strata/components/engine/
  echo -n "  table rows: "; grep -c "^f16o" /data/gfx906-rocblas-5.7.0.txt
'
echo "===== [3] 服务面 ====="
printf '  health: '; curl -s --max-time 6 http://127.0.0.1:8090/health | head -c 90; echo
printf '  UI: '; curl -s -o /dev/null -w '%{http_code} %{size_download}B\n' --max-time 8 http://127.0.0.1:8090/
curl -s --max-time 6 http://127.0.0.1:8090/metrics | python3 -c "import sys,json;d=json.load(sys.stdin);e=d['engine'];h=d['hardware'];print('  slots=%d vram_free=%d pcie=%s gen=%s width=%s'%(e['expert_slots'],e['vram_free_mib'],e.get('pcie_frac'),h.get('gpu_pcie_gen'),h.get('gpu_pcie_width')))"
echo "===== [4] 门禁 / tip ====="
bash /home/albus/strata166/tmp/verify_patches.sh 2>&1 | grep -E "img=|GATE"
bash /home/albus/strata166/tmp/verify_tip.sh 2>&1 | tail -2
echo "===== [5] 表加载自证（最近一次启动） ====="
docker exec "$C" bash -lc "grep -a 'rocBLAS tuning enabled' /data/strata-huihui-ud-iq4_xs.log | tail -1"
