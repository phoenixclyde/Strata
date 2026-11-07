set +e
D=/home/albus/strata166/gfx029
O=/home/albus/strata166/termout
mkdir -p "$O"
echo "== $(date +%H:%M:%S) 打包 terminal（目标 linux-x86_64）"
docker run --rm --name strata-termbuild \
  -v "$D":/src:ro -v "$O":/out -v /home/albus/strata166/pkgcache:/cache \
  strata-gfx906:0.2.9 bash -lc '
set -e
python3 -V
python3 /src/packaging/package_terminal.py --out /out --cache /cache 2>&1 | tail -25
' 2>&1 | tail -30
echo
echo "===== 产物 ====="
ls -lh "$O" 2>/dev/null | head -5
