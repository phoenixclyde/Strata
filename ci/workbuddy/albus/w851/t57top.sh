set +e
TBL=/home/albus/strata166/data/gfx906-rocblas-5.7.0.txt
f=$(ls -t /home/albus/strata166/data/w851_tune57_*.log | head -1)
echo "===== 5.7 表里 gain 最大的 15 个 case ====="
grep -a "^best T=" "$f" | sed -E 's/^best T=([0-9]+) N=([0-9]+) K=([0-9]+) ldy=[0-9]+ solution=(-?[0-9]+) ms=([0-9.]+) default_ms=([0-9.]+) gain=([0-9.]+)/T=\1 N=\2 K=\3 gain=\7  \6 -> \5 ms/' | sort -t= -k4 -gr | head -15
echo
echo "===== T=256 与 T=512 两个桶的全部 28 行（旧表完全没有） ====="
awk 'NR>4 && ($5==256 || $5==512){printf "  %-40s\n", $0}' "$TBL"
