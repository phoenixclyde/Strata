set +e
C=strata166-407
echo "===== [1] terminal 现在能不能真用 ====="
echo -n "  strata --version: "; docker exec "$C" /usr/local/bin/strata --version 2>&1 | head -1
echo "  strata status:"; docker exec "$C" /usr/local/bin/strata status 2>&1 | head -14 | sed 's/^/    /'
echo
echo "===== [2] 指纹 ====="
docker inspect "$C" --format 'image={{.Config.Image}} id={{slice .Id 0 12}} started={{.State.StartedAt}} restarts={{.RestartCount}} PORT={{range .Config.Env}}{{if eq (printf "%.4s" .) "PORT"}}{{.}}{{end}}{{end}}'
docker image inspect strata-gfx906:0.2.9t2 --format 'img id={{.Id}} size={{.Size}}'
docker ps -a --filter "name=strata166-407" --format '  {{.Names}}  {{.Status}}  {{.Image}}'
echo
echo "===== [3] 门禁 / 服务面 ====="
bash /home/albus/strata166/tmp/verify_patches.sh 2>&1 | grep -E "img=|GATE"
curl -s --max-time 6 http://127.0.0.1:8090/health | head -c 130; echo
curl -s --max-time 6 http://127.0.0.1:8090/metrics | python3 -c "import sys,json;d=json.load(sys.stdin);e=d['engine'];print('  slots=%d vram_free=%d pcie=%s'%(e['expert_slots'],e['vram_free_mib'],e.get('pcie_frac')))"
echo
echo "===== [4] 镜像里 0.2.9 的成分清点 ====="
docker exec "$C" bash -lc 'ls /opt/strata; echo "-- terminal:"; /opt/strata/terminal/bin/strata --version; echo "-- seed:"; du -sh /opt/strata/seed; echo "-- component:"; ls /opt/strata/components/engine/; echo "-- src:"; find /src -type f | wc -l'
