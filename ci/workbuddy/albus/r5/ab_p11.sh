#!/bin/bash
# W800e: STRATA_ROUTE_TAIL_SKIP 7(默认态,显式) vs 0  各 3 次，decode 96 token x 3 轮
cd /home/albus/strata166/tmp || exit 1
CFG=/home/albus/strata166/data/strata-huihui-ud-iq4_xs.json
LOG=/home/albus/strata166/data/strata-huihui-ud-iq4_xs.log
STAMP=$(date +%Y%m%d_%H%M%S)
OUT=/home/albus/strata166/data/w800_tailskip_$STAMP.txt
cp "$CFG" "$CFG.bak_w800e_$STAMP"
{
  echo "# W800e tail_skip $STAMP  arms: ON=7 OFF=0  | decode 96 tok x 3 turns"
} > "$OUT"
for rep in 1 2 3; do
  for arm in ON OFF; do
    if [ "$arm" = "ON" ]; then V=7; else V=0; fi
    python3 w800_setts.py "$V"
    docker restart strata166-407 >/dev/null 2>&1
    ok=0
    for i in $(seq 1 400); do
      curl -s --max-time 2 http://127.0.0.1:8090/health >/dev/null 2>&1 && { ok=$i; break; }
      sleep 1
    done
    echo "== ARM $arm rep $rep ready=${ok}s val=$V" >> "$OUT"
    python3 mt_dec.py 96 > /tmp/w800e.txt 2>&1
    cat /tmp/w800e.txt >> "$OUT"
    echo "" >> "$OUT"
  done
done
python3 w800_setts.py "" >/dev/null
docker restart strata166-407 >/dev/null 2>&1
echo "== DONE $OUT"
