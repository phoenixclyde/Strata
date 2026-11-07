set +e
f=/home/albus/strata166/data/w844_ab_190813.txt
echo "=== ARM B 段 ==="
sed -n '/=== ARM B/,/=== ARM A2/p' "$f" | grep -aE "MEDIAN|REQ arm|read in [0-9]+ ms|ABORT"
echo
echo "=== 全臂汇总（只取 read/median/REQ） ==="
grep -aE "^=== ARM|MEDIAN|REQ arm" "$f"
