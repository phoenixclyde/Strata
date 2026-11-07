
set +e
python3 /home/albus/strata166/tmp/state_q.py 2>&1
echo "@@@"
docker inspect strata166-407 --format 'started={{.State.StartedAt}} restarts={{.RestartCount}} image={{.Config.Image}} imgid={{.Image}}'
CFGJ=/home/albus/strata166/data/strata-huihui-ud-iq4_xs.json
EXEC=$(python3 -c "import json;print(json.load(open('$CFGJ'))['exe'])")
EXEH=$(printf '%s' "$EXEC" | sed 's#^/data/#/home/albus/strata166/data/#')
echo "exe=$EXEC"
md5sum "$EXEH" | awk '{print "binmd5="$1}'
md5sum "$CFGJ" | awk '{print "cfgmd5="$1}'
echo "@@@"
bash /home/albus/strata166/tmp/verify_patches.sh 2>&1 | tail -3
