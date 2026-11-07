S27=/home/albus/strata166/src0271
S28=/home/albus/strata166/src028
B=/home/albus/strata166/data/bin/strata-0.1.54n
echo "=== A. engine patch markers in the two source trees ==="
printf '%-10s %-38s %-8s %-8s %-8s\n' MARK FILE src0271 src028 binary
check() {
  m="$1"; f="$2"
  a=$(grep -c -F -- "$m" "$S27/$f" 2>/dev/null || echo 0)
  b=$(grep -c -F -- "$m" "$S28/$f" 2>/dev/null || echo 0)
  c=$(grep -a -c -F -- "$m" "$B" 2>/dev/null || echo 0)
  printf '%-10s %-38s %-8s %-8s %-8s\n' "$m" "$f" "$a" "$b" "$c"
}
check W794 src/kernels/cuda/qsa_decode_attn.cu
check W795 "$(echo 3rdparty/mmq)"
check W793 CMakeLists.txt
check W788 src/kernels/cuda/fused_gr.cu
echo "--- where do these markers actually live? (src028) ---"
grep -rln -F "W794" "$S28/src" "$S28/include" 2>/dev/null | head -5
grep -rln -F "W795" "$S28" --include=*.cu --include=*.cuh --include=*.cpp --include=*.hpp 2>/dev/null | head -5
grep -rln -F "W793" "$S28/CMakeLists.txt" 2>/dev/null | head -3
grep -rln -F "W788" "$S28/src" 2>/dev/null | head -5
echo
echo "=== B. serve layer: patched artifacts vs the tree vs the image ==="
printf '%-46s %-10s %-10s\n' FILE size mtime
for f in /home/albus/strata166/patches/serve-telemetry.py.patched /home/albus/strata166/patches/serve-web-app.js.patched "$S27/serve/telemetry.py" "$S28/serve/telemetry.py" "$S27/serve/web/app.js" "$S28/serve/web/app.js"; do
  [ -f "$f" ] && printf '%-46s %-10s %s\n' "$(echo $f | sed 's#/home/albus/strata166/##')" "$(stat -c%s "$f")" "$(stat -c%y "$f" | cut -c1-16)"
done
echo "--- inside the running image ---"
docker exec strata166-407 bash -lc 'for f in /src/serve/telemetry.py /src/serve/web/app.js; do [ -f "$f" ] && printf "%-34s %s\n" "$f" "$(stat -c%s "$f")"; done'
