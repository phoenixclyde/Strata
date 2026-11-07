set +e
f=$(ls -t /home/albus/strata166/data/w852_ab101_*.txt 2>/dev/null | head -1)
echo "== $f  $(date +%H:%M:%S)"
grep -aE "^===== ARM|ready=|TABLE |ROCM |requests .*delta|prompt [0-9]+ tokens.*read in|MEDIAN|NOT READY|GATE" "$f" 2>/dev/null | tail -20
echo "--- 容器:"; docker ps --format '{{.Names}} {{.Status}}' | head -3
