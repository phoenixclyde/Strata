P=/home/albus/strata166/patches
S27=/home/albus/strata166/src0271
S28=/home/albus/strata166/src028
echo "=== A. what our telemetry patch added (first 50 diff lines) ==="
diff -u "$P/serve-telemetry.py.orig" "$P/serve-telemetry.py.patched" 2>/dev/null | head -50
echo
echo "=== B. is it present in the tree / image? ==="
for pat in "strata_telemetry" "telemetry_read_key" "gpu_util" "nvidia-smi" "rocm-smi"; do
  a=$(grep -c -F -- "$pat" "$P/serve-telemetry.py.orig" 2>/dev/null || echo 0)
  b=$(grep -c -F -- "$pat" "$P/serve-telemetry.py.patched" 2>/dev/null || echo 0)
  c=$(grep -c -F -- "$pat" "$S28/serve/telemetry.py" 2>/dev/null || echo 0)
  d=$(docker exec strata166-407 bash -lc "grep -c -F -- '$pat' /src/serve/telemetry.py" 2>/dev/null | tr -d '\r')
  printf '  %-22s orig=%-4s patched=%-4s tree=%-4s image=%s\n' "$pat" "$a" "$b" "$c" "$d"
done
echo
echo "=== C. web app: what the patch added ==="
diff -u "$P/serve-web-app.js.orig" "$P/serve-web-app.js.patched" 2>/dev/null | grep -E '^\+' | head -25
echo
echo "=== D. engine patches: real targets ==="
for m in STRATA_MMQ_TILE_J STRATA_GR_TILEV W788 W795 W793; do
  printf '  [%s] 0271: ' "$m"
  grep -rl -F -- "$m" "$S27/src" "$S27/CMakeLists.txt" "$S27/third_party/llama.cpp/ggml/src/ggml-cuda" 2>/dev/null | sed "s#$S27/##" | tr '\n' ' '
  printf '\n        028 : '
  grep -rl -F -- "$m" "$S28/src" "$S28/CMakeLists.txt" "$S28/third_party/llama.cpp/ggml/src/ggml-cuda" 2>/dev/null | sed "s#$S28/##" | tr '\n' ' '
  echo
done
