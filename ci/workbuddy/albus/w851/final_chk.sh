set +e
echo "===== 生产现状 ====="
docker inspect strata166-407 --format 'image={{.Config.Image}} id={{slice .Id 0 12}} started={{.State.StartedAt}} restarts={{.RestartCount}}'
python3 -c "import json;d=json.load(open('/home/albus/strata166/data/strata-huihui-ud-iq4_xs.json'));print('  exe=',d['exe']);print('  table=',d['env'].get('STRATA_ROCBLAS_TUNING'));print('  env_n=',len(d['env']))"
curl -s --max-time 6 http://127.0.0.1:8090/health | head -c 110; echo
curl -s --max-time 6 http://127.0.0.1:8090/metrics | python3 -c "import sys,json;e=json.load(sys.stdin)['engine'];print('  slots=%d vram_free=%d'%(e['expert_slots'],e['vram_free_mib']))"
echo "===== 门禁 + tip ====="
bash /home/albus/strata166/tmp/verify_patches.sh 2>&1 | grep -E "img=|GATE"
bash /home/albus/strata166/tmp/verify_tip.sh 2>&1 | tail -2
echo "===== 新表产物 ====="
ls -l /home/albus/strata166/data/gfx906-rocblas-*.txt | awk '{print "  "$5" "$9}'
