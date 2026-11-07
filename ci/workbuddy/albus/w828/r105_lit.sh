B=/home/albus/strata166/data/bin/strata-0.1.54n
S=/home/albus/strata166/src028
echo "== source literals vs binary literals =="
check() {
  lit="$1"; file="$2"
  in_src=$(grep -a -c -F -- "$lit" "$file" 2>/dev/null || true)
  in_bin=$(grep -a -c -F -- "$lit" "$B" 2>/dev/null || true)
  printf '  %-34s src(%s)=%s  bin=%s\n' "$lit" "$(basename $file)" "$in_src" "$in_bin"
}
check "MMQ tile" "$S/src/prefill/prefill.cpp"
check "MMQ tile" "$S/src/prefill/moe_mmq.cu"
check "K-quant prompt kernels from" "$S/src/prefill/mmq_kq_loader.cpp"
check "not found next to the engine" "$S/src/prefill/mmq_kq_loader.cpp"
check "prompt chunk auto:" "$S/src/prefill/prefill.cpp"
check "16-bit GEMMs run FP16" "$S/src/prefill/gemm.cu"
check "a speculative window holds 2.." "$S/src/program/generate.cpp"
echo
echo "== where is 'MMQ tile' actually printed from =="
grep -rn -a -F "MMQ tile" "$S/src" 2>/dev/null | head -4
echo
echo "== is the narrow build the shipped one? (window rows banner) =="
grep -rn -a -F "holds up to" "$S/src/program/generate.cpp" | head -3
grep -rn -a -F "verify windows hold" "$S/src" | head -3
