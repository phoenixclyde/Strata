set +e
f=$(ls -t /home/albus/strata166/data/w850_rocm_*.txt 2>/dev/null | head -1)
echo "== $f  $(date +%H:%M:%S)"
grep -aE "^===== ARM|^  ready=|^  rocm:|read in [0-9]+ ms|MEDIAN decode|^== 生产恢复|ABORT|NOT READY" "$f" | tail -20
echo "--- 容器:"; docker ps --format '{{.Names}} {{.Status}} {{.Image}}' | head -3
