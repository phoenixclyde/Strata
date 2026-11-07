set +e
f=$(ls -t /home/albus/strata166/data/w842_b_*.txt | head -1)
echo "== $f"; cat "$f"
echo "--- health now:"; curl -s --max-time 5 http://127.0.0.1:8090/health; echo
