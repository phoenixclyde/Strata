#!/bin/bash
# W800f: STRATA_PREFILL_CPU_SHARE 0(生产) vs auto —— 小 chunk 把稀有专家交给空闲 CPU 池
cd /home/albus/strata166/tmp || exit 1
CFG=/home/albus/strata166/data/strata-huihui-ud-iq4_xs.json
LOG=/home/albus/strata166/data/strata-huihui-ud-iq4_xs.log
STAMP=$(date +%Y%m%d_%H%M%S)
OUT=/home/albus/strata166/data/w800_cpushare_$STAMP.txt
cp "$CFG" "$CFG.bak_w800f_$STAMP"
{
  echo "# W800f cpu_share $STAMP  arms: A=0 B=auto | sizes 120,230,430,810,3098 | nproc=$(nproc)"
} > "$OUT"
for rep in 1 2 3; do
  for arm in A B; do
    if [ "$arm" = "A" ]; then V=0; else V=auto; fi
    python3 w800_setcs.py "$V"
    docker restart strata166-407 >/dev/null 2>&1
    ok=0
    for i in $(seq 1 400); do
      curl -s --max-time 2 http://127.0.0.1:8090/health >/dev/null 2>&1 && { ok=$i; break; }
      sleep 1
    done
    N0=$(wc -l < "$LOG")
    echo "== ARM $arm rep $rep ready=${ok}s val=$V log0=$N0" >> "$OUT"
    python3 mt_scan.py 120,230,430,810,3098 > /tmp/w800f.txt 2>&1
    cat /tmp/w800f.txt >> "$OUT"
    tail -n +$((N0 + 1)) "$LOG" | grep -E "prefill timing: [0-9]+ tokens|on the CPU|share [0-9]" >> "$OUT"
    echo "" >> "$OUT"
  done
done
python3 w800_setcs.py 0 >/dev/null
docker restart strata166-407 >/dev/null 2>&1
echo "== DONE $OUT"
