date +%H:%M:%S
echo "--- progress ---"
grep -aE "ARM|READY|fit:" /home/albus/strata166/data/w830_ab.log 2>/dev/null | cut -c1-110
echo "--- containers ---"
docker ps --format '{{.Names}} {{.Status}}' | grep -E 'w830|strata166' || echo none
