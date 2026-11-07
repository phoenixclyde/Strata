set +e
R=/home/albus/strata166
echo "=== last gr_bench log ==="
tail -40 $R/data/w860_gr_bench.log 2>/dev/null
echo "=== cpp head ==="
sed -n '1,40p' $R/gfx029/src/kernels/fused_gr_bench.cpp
echo "=== includes ==="
grep -n "#include" $R/gfx029/src/kernels/fused_gr_bench.cpp
echo "=== size ==="
wc -l $R/gfx029/src/kernels/fused_gr_bench.cpp
echo "=== CMake target ==="
grep -n "fused_gr_bench" $R/gfx029/CMakeLists.txt | head -10
