#!/bin/bash
# W828i: stricter-gate arms (only extend the window when the draft is very likely right).
# tk = spec 8, min-p 0.85   tl = spec 8, min-p 0.90   (ta = prod baseline, already on disk)
set -eu
DATA=/home/albus/strata166/data
SRC=$DATA/strata-huihui-ud-iq4_xs.json
FP0=$(md5sum "$SRC" | cut -d' ' -f1)

python3 - "$SRC" <<'PY'
import json, sys, copy
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

arms = {'tk': (8, 0.85), 'tl': (8, 0.90)}
for name, (spec, mp) in arms.items():
    c = copy.deepcopy(base)
    a = set_arg(args, '--spec', spec)
    a = set_arg(a, '--spec-min-p', mp)
    c['args'] = a
    env = dict(c.get('env') or {})
    env['STRATA_DECODE_TIMING'] = '1'
    env['STRATA_SPEC_DEPTH'] = '1'
    c['env'] = env
    json.dump(c, open('/home/albus/strata166/data/w828_%s.json' % name, 'w'), ensure_ascii=False, indent=1)
    print(name, 'spec=%d minp=%.2f' % (spec, mp), 'nargs=%d' % len(a))
PY

FP1=$(md5sum "$SRC" | cut -d' ' -f1)
[ "$FP0" = "$FP1" ] && echo "PROD_UNCHANGED_OK" || { echo "!! PROD CHANGED"; exit 9; }
