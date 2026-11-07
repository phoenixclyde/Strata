B=/home/albus/strata166/data/bin/strata-0.1.54n
echo "== binary =="
file "$B"
echo "-- literal checks (no quotes in pattern) --"
for s in "MMQ tile" "K-quant prompt kernels" "windows hold up to" "strata 0.1.54" "STRATA_PREFILL_MMQ"; do
  n=$(grep -a -c -F -- "$s" "$B" || true)
  echo "  [$s] = $n"
done
echo
echo "== build-028 dir =="
ls -la /home/albus/strata166/src028/build-028/ | head -12
echo "rc_ls=$?"
echo "-- any ELF >10MB under build-028 --"
find /home/albus/strata166/src028/build-028 -maxdepth 3 -type f -size +10M -print 2>&1 | head
echo
echo "== md5 of shipped vs any build artifact =="
md5sum "$B"
find /home/albus/strata166/src028 -maxdepth 3 -name strata -type f -print -exec md5sum {} \; 2>&1 | head -8
echo
echo "== what r18_deploy did =="
sed -n '1,40p' /home/albus/strata166/tmp/r18_deploy.sh 2>/dev/null | cut -c1-140
