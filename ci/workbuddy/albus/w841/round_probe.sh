set +e
echo "=== A 生产实况 ==="
python3 /home/albus/strata166/tmp/state_q.py 2>&1 | tail -22
echo
echo "=== B 未被重启的证据 ==="
docker inspect strata166-407 --format 'started={{.State.StartedAt}} restarts={{.RestartCount}} image={{.Config.Image}}'
md5sum /home/albus/strata166/data/bin/strata-0.1.54n3
md5sum /home/albus/strata166/data/strata-huihui-ud-iq4_xs.json
echo
echo "=== C 门禁 ==="
bash /home/albus/strata166/tmp/verify_patches.sh 2>&1 | tail -6
