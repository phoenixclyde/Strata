#!/bin/bash
# W828k3: build the prefill-path arm config (prod + STRATA_PREFILL_MMQ=0 = FP16 everywhere).
set -eu
DATA=/home/albus/strata166/data
SRC=$DATA/strata-huihui-ud-iq4_xs.json
FP0=$(md5sum "$SRC" | cut -d' ' -f1)
python3 - "$SRC" <<'PY'
import json, sys, copy
base = json.load(open(sys.argv[1]))
for name, extra in (('tq', {'STRATA_PREFILL_MMQ': '0'}),
                    ('tp', {})):
    c = copy.deepcopy(base)
    env = dict(c.get('env') or {})
    env.update(extra)
    c['env'] = env
    json.dump(c, open('/home/albus/strata166/data/w828_%s.json' % name, 'w'), ensure_ascii=False, indent=1)
    print(name, extra, 'nargs=%d nenv=%d' % (len(c['args']), len(env)))
PY
FP1=$(md5sum "$SRC" | cut -d' ' -f1)
[ "$FP0" = "$FP1" ] && echo "PROD_UNCHANGED_OK" || { echo "!! PROD CHANGED"; exit 9; }
