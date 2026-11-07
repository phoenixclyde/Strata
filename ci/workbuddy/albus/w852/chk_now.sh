set +e
echo "== $(date +%H:%M:%S)"
docker ps --format '{{.Names}} {{.Status}}' | head -2
printf 'health: '; curl -s --max-time 6 http://127.0.0.1:8090/health | head -c 110; echo
docker images strata-gfx906 --format '  {{.Tag}}  {{.ID}}' | head -8
echo "--- clone:"
du -sh /home/albus/strata166/rocm-libs 2>/dev/null || echo "  未 clone"
