set +e
C=strata166-407
echo "===== 生产 ====="
docker inspect "$C" --format 'image={{.Config.Image}} id={{slice .Id 0 12}} restarts={{.RestartCount}}'
python3 -c "import json;d=json.load(open('/home/albus/strata166/data/strata-huihui-ud-iq4_xs.json'));print('  env_n=%d table=%s'%(len(d['env']), d['env'].get('STRATA_ROCBLAS_TUNING')));print('  TIMING越界?', 'STRATA_PREFILL_TIMING' in d['env'])"
printf '  health: '; curl -s --max-time 6 http://127.0.0.1:8090/health | head -c 80; echo
bash /home/albus/strata166/tmp/verify_patches.sh 2>&1 | grep -E "img=|GATE"
bash /home/albus/strata166/tmp/verify_tip.sh 2>&1 | tail -1
echo "===== 分支 ====="
git -C /home/albus/strata166/gfx-hblt log --oneline -2 | sed 's/^/  /'
git -C /home/albus/strata166/gfx-hblt ls-tree -r --name-only HEAD docs/hipblaslt-gfx906 | sed 's/^/    /'
git -C /home/albus/strata166/gfx-hblt rev-parse --short origin/gfx906/hipblaslt-vega20 2>/dev/null | sed 's/^/  origin=/' 
echo "===== 生产树 ====="
git -C /home/albus/strata166/gfx029 rev-parse --abbrev-ref HEAD; git -C /home/albus/strata166/gfx029 status --porcelain | wc -l
echo "===== rocm-libs（P0 探针前置） ====="
du -sh /home/albus/strata166/rocm-libs 2>/dev/null; find /home/albus/strata166/rocm-libs -type f -not -path '*/.git/*' 2>/dev/null | wc -l
