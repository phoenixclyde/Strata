#!/bin/bash
# W828k4: prefill CPU-share A/B by TTFT. ts = prod + STRATA_PREFILL_CPU_SHARE=0.
set -eu
DATA=/home/albus/strata166/data
SRC=$DATA/strata-huihui-ud-iq4_xs.json
FP0=$(md5sum "$SRC" | cut -d' ' -f1)
python3 - "$SRC" <<'PY'
import json, sys, copy
base = json.load(open(sys.argv[1]))
c = copy.deepcopy(base)
env = dict(c.get('env') or {})
env['STRATA_PREFILL_CPU_SHARE'] = '0'
c['env'] = env
json.dump(c, open('/home/albus/strata166/data/w828_ts.json', 'w'), ensure_ascii=False, indent=1)
print('ts CPU_SHARE=0  (prod was', base['env'].get('STRATA_PREFILL_CPU_SHARE'),
      '/ MAX', base['env'].get('STRATA_PREFILL_CPU_SHARE_MAX'), ') nenv=%d' % len(env))
PY
FP1=$(md5sum "$SRC" | cut -d' ' -f1)
[ "$FP0" = "$FP1" ] && echo "PROD_UNCHANGED_OK" || { echo "!! PROD CHANGED"; exit 9; }
