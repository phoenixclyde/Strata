set +e
L=/home/albus/strata166/data/strata-huihui-ud-iq4_xs.log
echo "=== (1) decode waited ms in fetches —— 分布 ==="
grep -a -oE "decode waited [0-9]+ ms in [0-9]+ fetches" $L \
 | sed -E 's/decode waited ([0-9]+) ms in ([0-9]+) fetches/\1 \2/' \
 | awk '{w+=$1; f+=$2; n++; if($1>mx)mx=$1; if(mn==""||$1<mn)mn=$1; h[int($1/100)]++} END{
     printf "n=%d  total_waited=%.1fs  mean=%.1f ms  min=%d  max=%d  mean_fetches=%.1f\n", n, w/1000, w/n, mn, mx, f/n;
     print "--- 直方图 (100ms 桶, 桶号=开始值) ---";
     for(i=0;i<=30;i++) if(h[i]>0) printf "  %4d-%4d ms : %d\n", i*100, i*100+99, h[i];
   }'
echo
echo "=== (2) ms per token（adaptive tier 自报） ==="
grep -a -oE "[0-9.]+ against [0-9.]+ ms per token|[0-9.]+% \([0-9.]+ ms per token\)" $L | sort | uniq -c | sort -rn | head -12
echo
echo "=== (3) async tier per round ==="
grep -a -oE "[0-9]+ rounds, [0-9]+ experts swapped in, [0-9.]+ ms per round" $L | awk -F'[ ,]+' '{r+=$1;e+=$2;m+=$(NF-2); n++} END{printf "n=%d rounds=%.0f experts=%.0f mean_round=%.2f ms\n", n,r,e,m/n}'
grep -a -oE "[0-9.]+ ms per round" $L | awk '{s+=$1;n++} END{printf "ms/round: n=%d mean=%.2f\n",n,s/n}'
echo
echo "=== (4) verify timeout 上下文 ==="
grep -a -n "verify: timed out" $L | head -5
echo "--- 这些行前后 3 行 ---"
for n in $(grep -a -n "verify: timed out" $L | cut -d: -f1 | head -3); do
  echo "### line $n"
  sed -n "$((n-3)),$((n+1))p" $L | cut -c1-220
done
echo
echo "=== (5) resident RAM 数值分布 ==="
grep -a -oE "resident RAM: [0-9.]+ GiB of experts in RAM, [0-9]+ exchanged" $L | sed -E 's/resident RAM: ([0-9.]+) GiB.*, ([0-9]+) exchanged/\1 \2/' | sort -u | head -10
