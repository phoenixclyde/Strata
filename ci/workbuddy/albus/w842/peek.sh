set +e
f=$(ls -t /home/albus/strata166/data/w842_simt2_*.txt | head -1)
echo "file=$f  $(date +%H:%M:%S)"
grep -aE "^=== ARM|^  READ |^  SEL |^  DT |read in|ABORT|slots=" "$f" | tail -22
echo "--- 容器:"; docker ps --format '{{.Names}} {{.Status}}' | head -2
