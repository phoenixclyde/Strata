#!/usr/bin/env bash
# R40: --prompt-cache-every 8192 -> 1024, then measure incremental reuse.
# Backup first; the rollback is one cp + one restart.
set -u
CFG=/home/albus/strata166/data/strata-huihui-ud-iq4_xs.json
BAK=$CFG.w863r40.bak

echo "=== 0. backup ==="
cp -a "$CFG" "$BAK"
ls -l "$BAK" | awk '{print $5, $9}'
echo "rollback: cp $BAK $CFG && docker restart strata166-407"

echo
echo "=== 1. change the one parameter ==="
python3 - <<'PY'
import json
p = '/home/albus/strata166/data/strata-huihui-ud-iq4_xs.json'
d = json.load(open(p))
a = d['args']
i = a.index('--prompt-cache-every')
old = a[i + 1]
a[i + 1] = '1024'
json.dump(d, open(p, 'w'), indent=2, ensure_ascii=False)
print('prompt-cache-every: %s -> %s' % (old, a[i + 1]))
print('prompt-cache      :', a[a.index('--prompt-cache') + 1] if '--prompt-cache' in a else '(default 6)')
PY

echo
echo "=== 2. restart (about 250 s) ==="
docker restart strata166-407 >/dev/null 2>&1
T0=$(date +%s)
for i in $(seq 1 50); do
  sleep 8
  H=$(curl -s --max-time 3 http://127.0.0.1:8090/health 2>/dev/null || true)
  case "$H" in
    *'"ok"'*) echo "healthy after $(( $(date +%s) - T0 ))s"; break ;;
  esac
done
curl -s --max-time 5 http://127.0.0.1:8090/health | head -c 180
echo

echo
echo "=== 3. the same measurement as the baseline ==="
cd /home/albus/strata166/ci && python3 prefill_ab.py --n 3

echo
echo "=== 4. cold curve must be unchanged (proves the edit touches reuse only) ==="
cd /home/albus/strata166/ci && python3 - <<'PY'
import sys
sys.argv = ['x']
src = open('prefill_probe.py').read()
src = src.replace("for approx in (256, 512, 1024, 2048, 4096, 8192):", "for approx in (2048, 4096):")
exec(compile(src.replace('if __name__ == "__main__":\n    main()', 'main()'), 'probe', 'exec'))
PY
echo
echo "=== 5. gate ==="
cd /home/albus/strata166/ci && . ./config.sh && python3 gate.py --repo "$REPO" --build "$BUILD" --config "$CFG" 2>&1 | tail -4
