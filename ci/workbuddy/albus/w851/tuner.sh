set +e
D=/home/albus/strata166/gfx029
echo "===== [1] tune_rocblas.cpp 的用法 / 参数 ====="
sed -n '1,60p' "$D/tools/hip/tune_rocblas.cpp"
echo
echo "===== [2] 它怎么挑形状（shape 列表从哪来） ====="
grep -n "shape\|Shape\|N\b\|K\b\|T\b\|for (" "$D/tools/hip/tune_rocblas.cpp" | head -30
echo
echo "===== [3] 输出格式与结束 ====="
sed -n '250,300p' "$D/tools/hip/tune_rocblas.cpp"
echo
echo "===== [4] CMake 里 tune_rocblas 的 target ====="
grep -n "tune_rocblas" "$D/CMakeLists.txt" "$D/tools/CMakeLists.txt" 2>/dev/null | head -10
