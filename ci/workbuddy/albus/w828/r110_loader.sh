S=/home/albus/strata166/src028
echo "S=$S"
echo "--- loader: first 55 lines ---"
sed -n '1,55p' "$S/src/prefill/mmq_kq_loader.cpp"
echo "--- loader: where it looks for kernels ---"
grep -n "path\|dlopen\|so\b\|cubin\|hsaco\|engine" "$S/src/prefill/mmq_kq_loader.cpp" | head -14
echo "--- callers ---"
grep -rn "mmq_kq" "$S/src" "$S/CMakeLists.txt" | head -10
echo "--- build option that compiles this file ---"
grep -n "mmq_kq_loader\|MMQ_KQ" "$S/CMakeLists.txt" | head -10
