#!/bin/bash
# W828h: build the spec-window arms (cap x gate) from the production config.
# Arms:  ta = prod (spec 4, min-p 0.70)          -- baseline
#        tf = spec 8, min-p 0.70                  -- cap raised, gate unchanged
#        tg = spec 8, min-p 0.50                  -- cap raised + upstream default gate
#        th = spec 8, min-p 0.50 + SPEC_COST=1    -- the engine's own cost-aware window rule
set -eu
DATA=/home/albus/strata166/data
SRC=$DATA/strata-huihui-ud-iq4_xs.json
mkdir -p "$DATA/w828_trace"
FP0=$(md5sum "$SRC" | cut -d' ' -f1)
cp -a "$SRC" "$DATA/strata-huihui-ud-iq4_xs.json.bak-w828h"

python3 - "$SRC" <<'PY'
import json, sys, copy, os
src = sys.argv[1]
base = json.load(open(src))
args = list(base['args'])

def set_arg(a, key, val):
    a = list(a)
    if key in a:
        a[a.index(key) + 1] = str(val)
    else:
        a += [key, str(val)]
    return a

arms = {
    # name: (spec, min_p, extra env)
    'ta': (4, 0.70, {}),
    'tf': (8, 0.70, {}),
    'tg': (8, 0.50, {}),
    'th': (8, 0.50, {'STRATA_SPEC_COST': '1'}),
}
for name, (spec, mp, extra) in arms.items():
    c = copy.deepcopy(base)
    a = set_arg(args, '--spec', spec)
    a = set_arg(a, '--spec-min-p', mp)
    c['args'] = a
    env = dict(c.get('env') or {})
    env['STRATA_DECODE_TIMING'] = '1'
    env['STRATA_SPEC_DEPTH'] = '1'
    env['STRATA_SPEC_TRACE'] = '/data/w828_trace/spec_%s.txt' % name
    env.update(extra)
    c['env'] = env
    out = '/home/albus/strata166/data/w828_%s.json' % name
    json.dump(c, open(out, 'w'), ensure_ascii=False, indent=1)
    print(name, 'spec=%d minp=%.2f' % (spec, mp), 'extra=%s' % extra,
          'nargs=%d nenv=%d' % (len(a), len(env)))
PY

FP1=$(md5sum "$SRC" | cut -d' ' -f1)
echo "prod fingerprint $FP0 -> $FP1"
[ "$FP0" = "$FP1" ] && echo "PROD_UNCHANGED_OK" || { echo "!! PROD CHANGED"; exit 9; }

echo "--- arms on disk ---"
for a in ta tf tg th; do
  python3 -c "
import json;c=json.load(open('/home/albus/strata166/data/w828_$a.json'))
a=c['args']
print('$a', 'spec='+a[a.index('--spec')+1], 'minp='+a[a.index('--spec-min-p')+1],
      'cost='+str((c.get('env') or {}).get('STRATA_SPEC_COST','-')))
"
done
echo "--- engine binary ---"
python3 -c "
import json;c=json.load(open('/home/albus/strata166/data/w828_tf.json'));print(c['exe'])"
