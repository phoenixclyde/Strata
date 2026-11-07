date +%H:%M:%S
for a in ta tc; do
  echo "===== $a"
  grep -a "strata decode timing" /home/albus/strata166/data/w828_$a.log | tail -4 | tail -3 | cut -c1-300
done
echo "--- running ---"
docker ps --format '{{.Names}} {{.Status}}' | grep w828 || echo none
