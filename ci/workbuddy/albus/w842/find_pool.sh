set +e
ls -l /home/albus/strata166/tmp/*.json 2>/dev/null | head -20
echo "--- mt_read 默认 pool ---"
grep -n "pool" /home/albus/strata166/tmp/mt_read.py | tail -8
