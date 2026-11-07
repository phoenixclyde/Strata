date +%H:%M:%S
echo "--- A/B log so far ---"
grep -aE "ARM|READY|fit:|warm-up" /home/albus/strata166/data/w830_ab.log 2>/dev/null | cut -c1-120
echo "--- containers ---"
docker ps -a --format '{{.Names}} {{.Status}}' | grep -E 'w830|strata166' | head -5
