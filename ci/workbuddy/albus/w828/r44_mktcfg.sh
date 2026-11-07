set -e
cd /home/albus/strata166
python3 - <<'PY'
import json
base=json.load(open('/home/albus/strata166/data/strata-huihui-ud-iq4_xs.json'))
def mk(name, adapt):
    c=json.loads(json.dumps(base))
    c['exe']='/data/bin/strata-0.1.54n'
    c['log']='/data/%s.log' % name
    c['env']=dict(c.get('env') or {})
    c['env']['STRATA_DECODE_TIMING']='1'   # W828b: the anti-noise ruler (ms/window), P175/W807
    if adapt:
        c['args']=c['args']+['--adapt-every','1','--adapt-swaps','80','--adapt-decay','0.97']
    json.dump(c, open('/home/albus/strata166/data/%s.json'%name,'w'), ensure_ascii=False, indent=1)
    print(name, 'args', len(c['args']), 'env', len(c['env']), 'adapt', adapt)
mk('w828_ta', False)
mk('w828_tb', True)
PY
grep -o '"STRATA_DECODE_TIMING": "[0-9]*"' /home/albus/strata166/data/w828_ta.json /home/albus/strata166/data/w828_tb.json
