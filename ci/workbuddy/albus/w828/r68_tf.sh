set -e
cd /home/albus/strata166
python3 - <<'PY'
import json
base=json.load(open('/home/albus/strata166/data/w828_ta.json'))
c=json.loads(json.dumps(base))
c['log']='/data/w828_tf.log'
c['parallel']=2               # serve turns this into --batch 2
json.dump(c, open('/home/albus/strata166/data/w828_tf.json','w'), ensure_ascii=False, indent=1)
print('tf parallel', c['parallel'], 'args', len(c['args']), 'env', len(c['env']))
PY
cp -f /home/albus/strata166/tmp/mt_gen2.py /home/albus/strata166/tmp/mt_gen2.py 2>/dev/null || true
cd /home/albus/strata166/tmp
pkill -f w828_ab2.sh 2>/dev/null || true
for a in tf; do rm -f /home/albus/strata166/data/w828_${a}_batch.log /home/albus/strata166/data/w828_tf.log; done
setsid nohup bash /home/albus/strata166/tmp/w828_arm3.sh tf /data/w828_tf.json w828tf 900 > /home/albus/strata166/data/w828_ab6.log 2>&1 < /dev/null &
sleep 20
date +%H:%M:%S
docker ps --format '{{.Names}} {{.Status}}' | grep -E 'w828|strata166' || echo none
head -8 /home/albus/strata166/data/w828_ab6.log
