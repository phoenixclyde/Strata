set +e
echo "=== 生产状态 ==="
docker ps --format '{{.Names}} {{.Status}}' | head -2
curl -s --max-time 5 http://127.0.0.1:8090/health; echo
python3 -c "import json;d=json.load(open('/home/albus/strata166/data/strata-huihui-ud-iq4_xs.json'));print('exe=',d['exe'],'env_n=',len(d.get('env') or {}))"
echo
echo "=== A2 臂的完整指标（n4 + SIMT=1） ==="
grep -aE "^=== ARM|read in [0-9]+ ms|slots=" /home/albus/strata166/data/w842_simt2_20261031_181616.txt | sed -n '1,20p'
echo
echo "=== 门禁 ==="
bash /home/albus/strata166/tmp/verify_patches.sh 2>&1 | tail -3
