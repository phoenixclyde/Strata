cd /home/albus/strata166/tmp
echo "=== decode 5x128 ==="
python3 mt_gen.py 8090 b154n /home/albus/strata166/tmp/w828_b154n_dec.json dec_corpus.json 128 5 2>&1 | tail -8
echo "=== read sweep (warm 2) ==="
python3 mt_read.py 8090 b154n /home/albus/strata166/tmp/w828_b154n_read.json 1500,3000,6000 1 kl_pool.json 0 2 2>&1 | tail -10
echo "=== engine log ==="
docker logs w828b154n 2>&1 | tail -400 > /home/albus/strata166/tmp/w828_b154n.log
grep -a "strata prefill timing" /home/albus/strata166/tmp/w828_b154n.log | tail -4 | cut -c1-185
echo "=== cache line ==="
grep -a -E "expert cache auto|allocated after the cache|expert arena:" /home/albus/strata166/tmp/w828_b154n.log | tail -4 | cut -c1-185
