set +e
D=/home/albus/strata166/gfx029
echo "===== [1] hipBLASLt 在源码里的完整用法 ====="
grep -rn "hipblaslt\|hipblasLt\|HIPBLASLT" "$D/src" "$D/include" "$D/CMakeLists.txt" "$D/cmake" 2>/dev/null | head -30
echo
echo "===== [2] 哪一个宏/分支决定用 hipBLASLt（gfx906 走不走） ====="
grep -rn "STRATA_HIPBLASLT\|USE_HIPBLASLT\|GFX906" "$D/CMakeLists.txt" 2>/dev/null | head -20
echo
echo "===== [3] tools/hip 下的 tuning 表清单（上游给了哪些 arch） ====="
ls -R "$D/tools/hip" 2>/dev/null | head -40
