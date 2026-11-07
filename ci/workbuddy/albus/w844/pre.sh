set +e
cd /home/albus/strata166/gfx906
echo "=== 分支状态 ==="
git fetch origin 2>&1 | tail -2
echo "HEAD=$(git rev-parse --short HEAD)  origin/main=$(git rev-parse --short origin/main)"
echo -n "behind/ahead vs origin/main: "; git rev-list --left-right --count origin/main...HEAD
echo "=== 树完整性 ==="
ls -d third_party/llama.cpp 2>/dev/null || echo "NO third_party/llama.cpp"
ls third_party 2>/dev/null | head -5
echo "=== 磁盘 ==="
df -h /home/albus | tail -1
echo "=== src028 基底（找版本串） ==="
grep -rn "0\.2\.[0-9]" /home/albus/strata166/src028/CMakeLists.txt | head -3
echo "=== gfx906 树的版本串 ==="
grep -rn "0\.2\.[0-9]" /home/albus/strata166/gfx906/CMakeLists.txt | head -3
echo "=== 现有构建目录 ==="
ls -d /home/albus/strata166/src028/build-* /home/albus/strata166/gfx906/build-* 2>/dev/null
