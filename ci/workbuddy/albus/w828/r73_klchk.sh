date +%H:%M:%S
ls -la /home/albus/strata166/data/w828kl/ 2>/dev/null
for f in /home/albus/strata166/data/w828kl/*.tsv; do
  [ -f "$f" ] || continue
  echo "== $f  lines=$(wc -l < $f)  md5=$(md5sum $f | cut -d' ' -f1)"
  head -1 "$f" | cut -c1-120
done
echo "--- eall progress ---"
docker ps --format '{{.Names}} {{.Status}}' | grep w828 || echo none
tail -6 /home/albus/strata166/data/w828_kl.log | cut -c1-150
