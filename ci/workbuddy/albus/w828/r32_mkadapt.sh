set -e
cd /home/albus/strata166
docker rm -f w828calib >/dev/null 2>&1 || true
python3 - <<'PY'
import json
base=json.load(open('/home/albus/strata166/data/w828_b154n.json'))
b=json.loads(json.dumps(base))
b['log']='/data/w828_b154na.log'
b['args']=b['args']+['--adapt-every','1','--adapt-swaps','80','--adapt-decay','0.97']
json.dump(b, open('/home/albus/strata166/data/w828_b154na.json','w'), ensure_ascii=False, indent=1)
print('A exe', base['exe'], len(base['args']), 'args')
print('B exe', b['exe'], len(b['args']), 'args ->', b['args'][-6:])
PY
