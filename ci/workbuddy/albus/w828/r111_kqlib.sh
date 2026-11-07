S=/home/albus/strata166/src028
echo "== the K-quant kernel library, anywhere in the tree =="
find "$S" -maxdepth 4 -name '*strata_kq*' -o -maxdepth 4 -name 'libstrata_kq*' 2>/dev/null | head
echo
echo "== what is next to the engine in production =="
ls -la /home/albus/strata166/data/bin/ | head -12
echo
echo "== does any built binary/library mention the loader banner =="
for f in $(find "$S" -maxdepth 4 -type f \( -name 'strata*' -o -name 'libstrata_kq*' \) -size +1M 2>/dev/null | head -6); do
  n=$(grep -a -c -F "K-quant prompt kernels" "$f" 2>/dev/null || true)
  printf '  %-58s banner=%s\n' "$(basename $(dirname $f))/$(basename $f)" "$n"
done
echo
echo "== KQ library name macro =="
grep -rn "STRATA_KQ_LIB_NAME" "$S/src" "$S/CMakeLists.txt" "$S/include" 2>/dev/null | head -6
echo
echo "== build option state that matters (narrow build log) =="
grep -nE "STRATA_MMQ_KQUANTS|strata_kq|MMQ_KQ" "$S/build-028.log" 2>/dev/null | head -8
