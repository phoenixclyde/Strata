set -e
cd /home/albus/strata166
python3 - <<'PY'
import json
base=json.load(open('/home/albus/strata166/data/w828_ta.json'))
c=json.loads(json.dumps(base))
c['log']='/data/w828_te.log'
c['env']=dict(c['env'])
# the two remaining gfx1151 decode-side items that could plausibly work on wave64:
#   EXPERT_V2  grouped decode experts  (only V2K was measured here before, not V2)
#   GDN_SPLIT  the GDN step over 4 blocks per head (doc: 3-13% on a window of 2+ rows)
c['env']['STRATA_EXPERT_V2']='1'
c['env']['STRATA_GDN_SPLIT']='1'
json.dump(c, open('/home/albus/strata166/data/w828_te.json','w'), ensure_ascii=False, indent=1)
print('te env:', sorted(k for k in c['env'] if k.startswith('STRATA_EXPERT_V2') or k=='STRATA_GDN_SPLIT'))
PY
cd /home/albus/strata166/tmp
pkill -f w828_ab2.sh 2>/dev/null || true
for a in te; do rm -f /home/albus/strata166/data/w828_ab2_$a.txt /home/albus/strata166/data/w828_$a.log; done
setsid nohup bash /home/albus/strata166/tmp/w828_ab2.sh te te > /home/albus/strata166/data/w828_ab5.log 2>&1 < /dev/null &
sleep 18
date +%H:%M:%S
docker ps --format '{{.Names}} {{.Status}}' | grep -E 'w828|strata166' || echo none
