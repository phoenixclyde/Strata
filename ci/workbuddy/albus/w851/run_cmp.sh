set +e
f=$(ls -t /home/albus/strata166/data/w851_tune55_*.log | head -1)
echo "===== 5.5 tune 摘要 ====="
head -2 "$f"; echo -n "  case: "; grep -ac "^case T=" "$f"; echo -n "  best: "; grep -ac "^best T=" "$f"
echo -n "  平均 gain: "; grep -a "^best T=" "$f" | sed -E 's/.*gain=([0-9.]+)/\1/' | awk '{s+=$1;n++} END{printf "%.2f (n=%d)\n", s/n, n}'
echo -n "  gain>=2.0: "; grep -a "^best T=" "$f" | sed -E 's/.*gain=([0-9.]+)/\1/' | awk '$1>=2.0' | wc -l
tail -2 "$f"
echo
python3 /home/albus/strata166/tmp/w851_cmp.py
