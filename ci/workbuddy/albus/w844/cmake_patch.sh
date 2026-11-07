set +e
D=/home/albus/strata166/gfx029
echo "=== 打 CMake 两个标记（幂等，带锚点断言） ==="
python3 /home/albus/strata166/tmp/restore_cmake.py "$D/CMakeLists.txt" 2>&1 | tail -6
echo "--- 标记:"; grep -c "W793" "$D/CMakeLists.txt"; grep -c "W776 local" "$D/CMakeLists.txt"
echo
echo "=== third_party 是否含 llama.cpp ==="
ls "$D/third_party" | head
ls -d "$D/third_party/llama.cpp" 2>/dev/null || echo "NO llama.cpp in gfx029"
ls -d /home/albus/strata166/src028/third_party/llama.cpp 2>/dev/null && echo "src028 has llama.cpp"
echo
echo "=== 新树改动面（git status） ==="
git -C "$D" status --porcelain | head -15
echo "--- 计数:"; git -C "$D" status --porcelain | wc -l
