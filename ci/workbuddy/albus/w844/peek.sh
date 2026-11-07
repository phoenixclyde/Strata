set +e
f=$(ls -t /home/albus/strata166/data/w844_ab_*.txt | head -1)
echo "== $f  $(date +%H:%M:%S)"
grep -aE "^=== ARM|REQ arm|read in [0-9]+ ms|MEDIAN|ABORT|VER " "$f" | tail -24
