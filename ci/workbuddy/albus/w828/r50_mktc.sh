set -e
cd /home/albus/strata166
python3 - <<'PY'
import json
base=json.load(open('/home/albus/strata166/data/w828_ta.json'))
c=json.loads(json.dumps(base))
c['log']='/data/w828_tc.log'
c['env']=dict(c['env']); c['env']['STRATA_SH_STREAM']='1'
json.dump(c, open('/home/albus/strata166/data/w828_tc.json','w'), ensure_ascii=False, indent=1)
print('tc env', sorted(c['env']))
print('ta env', sorted(base['env']))
PY
