set +e
C=strata166-407
L=$(ls -t /home/albus/strata166/data/w847_swap_*.txt | head -1)
echo "===== [1] 切换日志关键段（$L） ====="
sed -n '/-- 自证 --/,$p' "$L" | head -30
echo
echo "===== [2] 容器 / 镜像指纹 ====="
docker inspect "$C" --format 'image={{.Config.Image}} id={{slice .Id 0 12}} started={{.State.StartedAt}} restarts={{.RestartCount}} status={{.State.Status}}'
docker image inspect strata-gfx906:0.2.9 --format 'img_id={{.Id}} size={{.Size}}'
echo "--- 三代容器都在:"
docker ps -a --filter "name=strata166-407" --format '  {{.Names}}  {{.Status}}  {{.Image}}'
echo
echo "===== [3] 容器内 /src 与树的一致性（关键 6 项） ====="
for f in serve/server.py serve/telemetry.py src/program/generate.cpp src/core/arch_defaults.cpp CMakeLists.txt include/strata/prefill/gdn_probe.hpp; do
  a=$(docker exec "$C" md5sum "/src/$f" 2>/dev/null | cut -d' ' -f1)
  b=$(md5sum "/home/albus/strata166/gfx029/$f" 2>/dev/null | cut -d' ' -f1)
  [ "$a" = "$b" ] && r=same || r=DIFF
  printf '  %-44s %s\n' "$f" "$r"
done
echo
echo "===== [4] 组件包（镜像内） ====="
docker exec "$C" bash -lc "ls /opt/strata/components/engine/; /opt/strata/components/engine/*/strata --version | head -1; python3 /src/packaging/package_engine.py --verify /opt/strata/components/engine/*/ 2>&1 | tail -1"
echo
echo "===== [5] 服务面 ====="
curl -s --max-time 6 http://127.0.0.1:8090/health | head -c 200; echo
printf '  UI: '; curl -s -o /dev/null -w '%{http_code} %{size_download}B\n' --max-time 8 http://127.0.0.1:8090/
curl -s --max-time 6 http://127.0.0.1:8090/metrics | python3 -c "import sys,json;d=json.load(sys.stdin);e=d['engine'];h=d['hardware'];print('  slots=%d vram_free=%d pcie=%s  gpu_pcie_gen=%s width=%s'%(e['expert_slots'],e['vram_free_mib'],e.get('pcie_frac'),h.get('gpu_pcie_gen'),h.get('gpu_pcie_width')))"
echo "  serve 报错:"; docker logs --tail 40 "$C" 2>&1 | grep -aiE "traceback|error|exception" | tail -3
