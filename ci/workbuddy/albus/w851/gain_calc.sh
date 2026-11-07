set +e
f=$(ls -t /home/albus/strata166/data/w851_tune55_*.log | head -1)
echo "===== 5.5：按 T 桶汇总 GEMM 时间（14 个形状各一次） ====="
grep -aE "^best T=|^keep_default T=" "$f" | awk '
{
  for(i=1;i<=NF;i++){
    if($i ~ /^T=/){split($i,a,"=");T=a[2]}
    if($i ~ /^default_ms=/){split($i,a,"=");D=a[2]}
    if($i ~ /^ms=/){split($i,a,"=");M=a[2]}
    if($i ~ /^best /){B=1}
  }
  if(B==1){sT[T]+=M; nT[T]++} else {sT[T]+=D; nT[T]++}
  sD[T]+=D; cT[T]++
  B=0
}
END{
  printf "  %-6s %-4s %-12s %-12s %-8s\n","桶","数","default 合计","最优合计","节省"
  for(t in cT)
    printf "  T=%-5d %-4d %8.2f ms   %8.2f ms   %5.1f%%\n", t, cT[t], sD[t], sT[t], (sD[t]-sT[t])/sD[t]*100
}' | sort -t= -k2 -n
echo
echo "===== 只看 T=256 / 512 的 28 行合计 ====="
grep -aE "^best T=(256|512) |^keep_default T=(256|512) " "$f" | awk '
{
  for(i=1;i<=NF;i++){if($i ~ /^default_ms=/){split($i,a,"=");D=a[2]}
                     if($i ~ /^ms=/){split($i,a,"=");M=a[2]}
                     if($i ~ /^best /){B=1}}
  sD+=D; sB+=(B==1?M:D); n++; B=0
}
END{printf "  %d 个形状: default 合计 %.2f ms -> 最优 %.2f ms  节省 %.1f%%\n", n, sD, sB, (sD-sB)/sD*100}'
