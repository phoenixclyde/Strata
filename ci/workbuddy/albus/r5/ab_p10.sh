#!/bin/bash
# W800c: STRATA_PREFILL_STREAM_MIN 三臂 A B C x 3 次，量小 chunk 的 wait copy / prompt_ms
cd /home/albus/strata166/tmp || exit 1
CFG=/home/albus/strata166/data/strata-huihui-ud-iq4_xs.json
LOG=/home/albus/strata166/data/strata-huihui-ud-iq4_xs.log
STAMP=$(date +%Y%m%d_%H%M%S)
OUT=/home/albus/strata166/data/w800_streammin_$STAMP.txt
cp "$CFG" "$CFG.bak_w800_$STAMP"
ARMS="A B C"
VAL_A=""
VAL_B="128"
VAL_C="64"
{
  echo "# W800c stream_min $STAMP  arms: A=absent B=128 C=64  sizes 120,230,430,810,3098"
} > "$OUT"
for rep in 1 2 3; do
  for arm in $ARMS; do
    eval "V=\$VAL_$arm"
    python3 w800_setenv.py "$V"
    docker restart strata166-407 >/dev/null 2>&1
    ok=0
    for i in $(seq 1 400); do
      curl -s --max-time 2 http://127.0.0.1:8090/health >/dev/null 2>&1 && { ok=$i; break; }
      sleep 1
    done
    N0=$(wc -l < "$LOG")
    echo "== ARM $arm rep $rep ready=${ok}s val='$V' log0=$N0" >> "$OUT"
    python3 mt_scan.py 120,230,430,810,3098 > /tmp/w800_scan.txt 2>&1
    cat /tmp/w800_scan.txt >> "$OUT"
    tail -n +$((N0 + 1)) "$LOG" | grep -E "prefill timing: [0-9]+ tokens|read [0-9]+ tokens \(batched\)|refilled [0-9]+ slots|lent [0-9]+ slots" >> "$OUT"
    echo "" >> "$OUT"
  done
done
python3 w800_setenv.py "" >/dev/null
docker restart strata166-407 >/dev/null 2>&1
echo "== DONE $OUT"
