P=/home/albus/strata166/patches
S27=/home/albus/strata166/src0271
S28=/home/albus/strata166/src028
IMG=strata166-407
echo "=== A. telemetry.py: tokens that ONLY our patch introduces ==="
for m in BW_REFRESH_S pcie_bw as returned from the FRU IOAccelerator powermetrics; do
  o=$(grep -c -F -- "$m" "$P/serve-telemetry.py.orig" 2>/dev/null | head -1)
  p=$(grep -c -F -- "$m" "$P/serve-telemetry.py.patched" 2>/dev/null | head -1)
  t=$(grep -c -F -- "$m" "$S28/serve/telemetry.py" 2>/dev/null | head -1)
  i=$(docker exec $IMG bash -lc "grep -c -F -- '$m' /src/serve/telemetry.py" 2>/dev/null | tr -d '\r')
  printf '  %-30s orig=%-3s patched=%-3s tree=%-3s image=%s\n' "$m" "$o" "$p" "$t" "$i"
done
echo
echo "=== B. web app: tokens that ONLY our patch introduces ==="
for m in saveApiKey "strata.apikey" "tab-btn-images" "api-key"; do
  p=$(grep -c -F -- "$m" "$P/serve-web-app.js.patched" 2>/dev/null | head -1)
  t=$(grep -c -F -- "$m" "$S28/serve/web/app.js" 2>/dev/null | head -1)
  i=$(docker exec $IMG bash -lc "grep -c -F -- '$m' /src/serve/web/app.js" 2>/dev/null | tr -d '\r')
  printf '  %-22s patched=%-3s tree=%-3s image=%s\n' "$m" "$p" "$t" "$i"
done
echo
echo "=== C. engine patch real targets ==="
for m in STRATA_MMQ_TILE_J STRATA_GR_TILEV W793 W795; do
  echo "  [$m]"
  echo -n "     0271: "; grep -rl -F -- "$m" "$S27" --include=*.cu --include=*.cuh --include=*.cpp --include=*.hpp --include=*.txt 2>/dev/null | sed "s#$S27/##" | head -4 | tr '\n' ' '; echo
  echo -n "     028 : "; grep -rl -F -- "$m" "$S28" --include=*.cu --include=*.cuh --include=*.cpp --include=*.hpp --include=*.txt 2>/dev/null | sed "s#$S28/##" | head -4 | tr '\n' ' '; echo
done
