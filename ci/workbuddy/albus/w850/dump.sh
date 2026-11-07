set +e
f=$(ls -t /home/albus/strata166/data/w850_rocm_*.txt | head -1)
echo "FILE=$f"
echo "===== 每臂的 rocBLAS/ROCm 自证 ====="
awk '/^===== ARM/{arm=$3} /^  rocm:|rocBLAS tuning|plain hipBLAS|prefill gemm/{print arm"  "$0}' "$f" | head -30
echo
echo "===== 每臂 read 与 decode ====="
awk '
/^===== ARM/{arm=$3; print "\n["arm"]"}
/read in [0-9]+ ms/{match($0,/prompt ([0-9]+) tokens/,a); match($0,/read in ([0-9]+) ms/,b); printf "  read  ptok=%-6s %s ms\n", a[1], b[1]}
/MEDIAN decode_tps/{print "  "$0}
' "$f"
echo
echo "===== 生产恢复确认 ====="
tail -6 "$f"
