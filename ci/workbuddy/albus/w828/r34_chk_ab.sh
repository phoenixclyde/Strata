date +%H:%M:%S
for a in b154n b154na; do
  f=/home/albus/strata166/data/w828_ab_$a.txt
  echo "== $a"
  grep -aE 'MEDIAN|READY=|ARM .* (cfg|end)|p[0-9] ' "$f" 2>/dev/null | tail -8
done
echo "--- running ---"
docker ps --format '{{.Names}} {{.Status}}' | grep w828 || echo none
