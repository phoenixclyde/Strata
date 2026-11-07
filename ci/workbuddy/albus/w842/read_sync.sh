set +e
grep -n "FILES\|PATCHERS\|for f in" -A12 /home/albus/strata166/tmp/sync_gfx906.sh | head -40
echo "=== 现有 LOCAL_PATCHES.tsv ==="
head -3 /home/albus/strata166/params/LOCAL_PATCHES.tsv 2>/dev/null || find /home/albus/strata166 -name LOCAL_PATCHES.tsv | head
