set +e
f=$(ls -t /home/albus/strata166/data/w851_tune57_*.log | head -1)
echo "== $f"
echo "===== [1] 头尾 ====="
head -2 "$f"; echo "..."; tail -8 "$f"
echo
echo "===== [2] 统计 ====="
echo -n "  case 数: "; grep -ac "^case T=" "$f"
echo -n "  有解的 (best): "; grep -ac "^best T=" "$f"
echo -n "  keep_default: "; grep -ac "^keep_default" "$f"
echo -n "  no_solutions: "; grep -ac "^no_solutions" "$f"
echo -n "  平均 gain: "; grep -a "^best T=" "$f" | sed -E 's/.*gain=([0-9.]+)/\1/' | awk '{s+=$1;n++} END{printf "%.2f  (n=%d)\n", s/n, n}'
echo -n "  gain>=2.0 的 case 数: "; grep -a "^best T=" "$f" | sed -E 's/.*gain=([0-9.]+)/\1/' | awk '$1>=2.0' | wc -l
echo
echo "===== [3] 表本身 ====="
TBL=/home/albus/strata166/data/gfx906-rocblas-5.7.0.txt
wc -l "$TBL"
echo "--- 表头:"
head -4 "$TBL"
echo "--- 每个 T 桶的行数:"
awk 'NR>4{print $5}' "$TBL" | sort -n | uniq -c | sed 's/^/   T=/'
echo "--- 每个 T 桶里 default 的行数:"
awk 'NR>4 && $6=="default"{print $5}' "$TBL" | sort -n | uniq -c | sed 's/^/   T=/'
