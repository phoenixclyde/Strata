set +e
DATA=/home/albus/strata166/data
OUT=$DATA/w846_gen_now.json
echo "== $(date +%H:%M:%S) 3x200tok decode（热态）"
( cd /home/albus/strata166/tmp && python3 mt_gen.py 8090 NOW "$OUT" dec_corpus.json 200 3 ) 2>&1 | grep -aE "p[0-9]|MEDIAN" | head -6
echo "== 门禁复跑"
bash /home/albus/strata166/tmp/verify_patches.sh 2>&1 | tail -2
echo "== 容器/健康"
docker ps --format '{{.Names}} {{.Status}}' | head -2
curl -s --max-time 5 http://127.0.0.1:8090/health | head -c 120; echo
