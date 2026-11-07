#!/bin/bash
# [W863] HC probe: does the hyper-connection read get cheaper when the Q8_0 path is off?
#
# One restart, two env changes, both of them non-arithmetic for the rest of the model:
#   STRATA_HC_Q8=0        -> the bf16 read instead of launch_q8() (the S23 experiment kernel)
#   STRATA_DECODE_TIMING=1 -> one phase table per request (logging only)
#
# Baseline for comparison: hc 6.89 ms/window with HC_Q8=1 (same binary 0.1.55h).
# This is a direction probe, not a measurement: if hc moves by >20% we do a proper
# interleaved A/B; if it moves by a few percent we stop here and revert.
set -u
CFG=/home/albus/strata166/data/strata-huihui-ud-iq4_xs.json
L=/home/albus/strata166/data/strata-huihui-ud-iq4_xs.log
BAK=/home/albus/strata166/ci/state/backups
TS=$(date +%Y%m%d_%H%M%S)
mkdir -p "$BAK"

echo "=== 1. backup config ==="
cp -f "$CFG" "$BAK/cfg_hcprobe_$TS.json"
echo "bak=$BAK/cfg_hcprobe_$TS.json"

echo "=== 2. set env ==="
python3 - "$CFG" <<'PY'
import json, sys
p = sys.argv[1]
d = json.load(open(p))
e = d.setdefault("env", {})
e["STRATA_HC_Q8"] = "0"
e["STRATA_DECODE_TIMING"] = "1"
json.dump(d, open(p, "w"), indent=2, ensure_ascii=False)
print("env:", sorted(e.items()))
PY

echo "=== 3. restart and wait ==="
docker restart strata166-407 >/dev/null 2>&1
OK=0
for i in $(seq 1 420); do
  if curl -s --max-time 2 http://127.0.0.1:8090/health >/dev/null 2>&1; then OK=$i; break; fi
  sleep 1
done
echo "health after ${OK}s"
sleep 8
echo "--- does the engine still say HC_Q8 is on? (it must NOT) ---"
grep -a 'STRATA_HC_Q8' "$L" | tail -2
grep -a 'hyper-connection read runs as' "$L" | tail -1

echo "=== 4. three requests ==="
for k in 1 2 3; do
  curl -s --max-time 180 http://127.0.0.1:8090/v1/chat/completions \
    -H 'Content-Type: application/json' \
    -d '{"model":"q","messages":[{"role":"user","content":"Count from 1 to 40, one number per line."}],"max_tokens":128,"stream":false}' \
    -o /dev/null
  echo "request $k done"
  sleep 2
done

echo "=== 5. phase tables (last 3) ==="
grep -a 'strata decode GPU stages' "$L" | tail -3

echo "=== 6. VRAM / health ==="
rocm-smi --showmeminfo vram 2>/dev/null | grep -i Used
curl -s --max-time 5 http://127.0.0.1:8090/health | head -c 120; echo
echo "PROBE_DONE"
