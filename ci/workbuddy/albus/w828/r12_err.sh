L=/home/albus/strata166/src028/build-028.log
echo "--- error lines ---"
grep -n -E 'error:|FAILED:' $L | head -30
echo "--- context ---"
grep -n -E 'error:' $L | head -1 | cut -d: -f1 | while read n; do sed -n "$((n-12)),$((n+18))p" $L; done
