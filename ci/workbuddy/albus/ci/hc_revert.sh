#!/bin/bash
# [W863] Revert the HC probe: restore the config backup (drops STRATA_HC_Q8 / STRATA_DECODE_TIMING)
# and restart.  The probe showed no signal larger than the phase table's own noise, so nothing
# is gained by leaving a non-default switch in production.
set -u
CFG=/home/albus/strata166/data/strata-huihui-ud-iq4_xs.json
BAK=/home/albus/strata166/ci/state/backups/cfg_hcprobe_20261101_172346.json
L=/home/albus/strata166/data/strata-huihui-ud-iq4_xs.log

echo "=== 1. restore config from backup ==="
[ -f "$BAK" ] || { echo "missing backup $BAK"; exit 1; }
cp -f "$BAK" "$CFG"
python3 -c "import json,sys;d=json.load(open(sys.argv[1]));print('env:',sorted(d.get('env',{}).items()))" "$CFG"
python3 -c "import json,sys;d=json.load(open(sys.argv[1]));print('exe:',d['exe'])" "$CFG"

echo "=== 2. restart ==="
docker restart strata166-407 >/dev/null 2>&1
OK=0
for i in $(seq 1 420); do
  if curl -s --max-time 2 http://127.0.0.1:8090/health >/dev/null 2>&1; then OK=$i; break; fi
  sleep 1
done
echo "health after ${OK}s"
sleep 8
curl -s --max-time 6 http://127.0.0.1:8090/health; echo

echo "=== 3. verify the default path is back ==="
grep -a 'STRATA_HC_Q8' "$L" | tail -1
grep -a 'native projection matrices' "$L" | tail -1
rocm-smi --showmeminfo vram 2>/dev/null | grep -i Used
echo REVERT_DONE
