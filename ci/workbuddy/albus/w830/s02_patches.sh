P=/home/albus/strata166/patches
echo "=== patches/ inventory ==="
ls -la "$P" 2>/dev/null | head -40
echo
echo "=== per-build patch dirs ==="
for d in /home/albus/strata166/build022/patches /home/albus/strata166/build023/patches /home/albus/strata166/build024/patches; do
  echo "[$d]"
  ls -la "$d" 2>/dev/null | head -12
done
echo
echo "=== what files do they touch? ==="
for f in "$P"/*.patch "$P"/*.diff /home/albus/strata166/build024/patches/*; do
  [ -f "$f" ] || continue
  t=$(grep -m3 -E '^\+\+\+ |^--- ' "$f" 2>/dev/null | tr '\n' ' ')
  echo "  $(basename $f)  ->  $t"
done
