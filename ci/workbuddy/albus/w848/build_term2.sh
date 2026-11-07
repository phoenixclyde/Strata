set +e
D=/home/albus/strata166/gfx029
O=/home/albus/strata166/termout
mkdir -p "$O"
COMMIT=$(git -C "$D" rev-parse HEAD 2>/dev/null | cut -c1-40)
echo "== $(date +%H:%M:%S) 打包 terminal，commit=$COMMIT"
docker run --rm --name strata-termbuild \
  -e STRATA_COMMIT="$COMMIT" \
  -v "$D":/src:ro -v "$O":/out -v /home/albus/strata166/pkgcache:/cache \
  strata-gfx906:0.2.9 bash -lc '
set -e
python3 /src/packaging/package_terminal.py --out /out --cache /cache --commit "$STRATA_COMMIT" 2>&1 | tail -22
' 2>&1 | tail -26
echo
echo "===== 产物 ====="
ls -lh "$O" 2>/dev/null | head -5
