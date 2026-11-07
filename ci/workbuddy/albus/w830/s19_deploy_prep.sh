S=/home/albus/strata166/src028
B=/home/albus/strata166/data/bin
echo "=== new binary ==="
ls -la "$S/build-028r/strata"
"$S/build-028r/strata" --version 2>&1 | head -2
echo
echo "=== deploy as strata-0.1.54n2 (cp -> .new -> mv, keep the old one) ==="
cp "$S/build-028r/strata" "$B/strata-0.1.54n2.new" && chmod +x "$B/strata-0.1.54n2.new" && mv "$B/strata-0.1.54n2.new" "$B/strata-0.1.54n2"
ls -la "$B" | tail -5
md5sum "$B/strata-0.1.54n2" "$S/build-028r/strata"
echo
echo "=== the rocBLAS path really is in this binary ==="
for s in "STRATA_ROCBLAS_TUNING" "rocblas_solution" "-rocblas-" "solution table"; do
  printf '  %-24s %s\n' "$s" "$(grep -a -c -F -- "$s" "$B/strata-0.1.54n2" 2>/dev/null || echo 0)"
done
echo
echo "=== rebuild the image with the merged telemetry (new tag, prod untouched) ==="
cat "$S/Dockerfile.w828" 2>/dev/null | head -12
docker build -q -t strata-gfx906:0.2.8p1 -f "$S/Dockerfile.w828" "$S" 2>&1 | tail -3
docker images | grep -E "strata-gfx906 +(0.2.8|0.2.8p1)" | head -3
docker run --rm strata-gfx906:0.2.8p1 bash -lc 'grep -c -F BW_REFRESH_S /src/serve/telemetry.py; python3 -m py_compile /src/serve/telemetry.py && echo PY_OK'
