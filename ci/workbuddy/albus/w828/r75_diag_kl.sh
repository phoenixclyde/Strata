date +%H:%M:%S
pkill -f w828_arm4.sh 2>/dev/null || true
for c in $(docker ps -aq --filter "name=w828"); do docker rm -f "$c" >/dev/null 2>&1; done
echo "=== e0 engine log: logpos lines ==="
grep -aiE "logpos" /home/albus/strata166/data/w828_kle0.log 2>/dev/null | head -8 | cut -c1-190
echo "=== last 12 lines of that log ==="
tail -12 /home/albus/strata166/data/w828_kle0.log 2>/dev/null | cut -c1-190
echo "=== the config's env (logpos + share) ==="
python3 -c "
import json;c=json.load(open('/home/albus/strata166/data/w828_kle0.json'))
e=c['env']; print({k:v for k,v in e.items() if 'LOGPOS' in k or 'SHARE' in k})"
echo "=== dir ==="
ls -la /home/albus/strata166/data/w828kl/ 2>/dev/null
