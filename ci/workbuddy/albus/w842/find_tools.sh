set +e
echo "=== tmp 里的构建脚本 ==="
grep -ln "cmake --build\|ninja" /home/albus/strata166/tmp/*.sh 2>/dev/null | head
echo
echo "=== 这些脚本里怎么调构建 ==="
grep -h "cmake --build\|/ninja\|ninja -C" /home/albus/strata166/tmp/*.sh /home/albus/strata166/tmp/*.py 2>/dev/null | sort -u | head -12
echo
echo "=== 可能的 cmake/ninja 位置 ==="
ls -l /usr/local/bin/cmake /usr/local/bin/ninja /opt/rocm/bin/cmake /opt/rocm/libexec/ninja 2>/dev/null
find /home/albus -maxdepth 3 -name "ninja" -type f 2>/dev/null | head -5
find /opt -maxdepth 4 -name "ninja" -type f 2>/dev/null | head -5
echo
echo "=== build.ninja 里记录的工具 ==="
grep -m3 "^rule CXX_COMPILER" -A3 /home/albus/strata166/src028/build-028r/build.ninja 2>/dev/null
grep -m1 "CMAKE_MAKE_PROGRAM\|CMAKE_COMMAND" /home/albus/strata166/src028/build-028r/CMakeCache.txt
