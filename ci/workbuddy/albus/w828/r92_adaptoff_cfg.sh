#!/bin/bash
# W828j: adaptive tier OFF (--adapt-swaps 0) vs production. Quality-neutral.
# ta = prod (adapt-every 4, adapt-swaps 96)   tm = prod + --adapt-swaps 0
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

c = copy.deepcopy(base)
a = set_arg(args, '--adapt-swaps', 0)
c['args'] = a
env = dict(c.get('env') or {})
env['STRATA_DECODE_TIMING'] = '1'
env['STRATA_SPEC_DEPTH'] = '1'
c['env'] = env
json.dump(c, open('/home/albus/strata166/data/w828_tm.json', 'w'), ensure_ascii=False, indent=1)
print('tm nargs=%d  adapt-swaps=%s  adapt-every=%s' % (
    len(a), a[a.index('--adapt-swaps') + 1],
    a[a.index('--adapt-every') + 1] if '--adapt-every' in a else '(default 4)'))
PY

FP1=$(md5sum "$SRC" | cut -d' ' -f1)
[ "$FP0" = "$FP1" ] && echo "PROD_UNCHANGED_OK" || { echo "!! PROD CHANGED"; exit 9; }
