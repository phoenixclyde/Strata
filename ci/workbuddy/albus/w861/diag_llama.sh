set +e
echo "=== routeB llama.cpp tree ==="
ls /home/albus/routeB/ML-gfx906/llama.cpp | head -20
find /home/albus/routeB/ML-gfx906/llama.cpp -maxdepth 3 -name "ggml.h" 2>/dev/null | head
echo "=== CMakeCache llama vars ==="
grep -i "llama" /home/albus/strata166/gfx029-build/CMakeCache.txt 2>/dev/null | head -20
echo "=== CMakeCache source dir ==="
grep -E "^CMAKE_HOME_DIRECTORY|^CMAKE_CACHEFILE_DIR" /home/albus/strata166/gfx029-build/CMakeCache.txt 2>/dev/null
echo "=== images ==="
docker images --format '{{.Repository}}:{{.Tag}} {{.Size}}' | head -12
echo "=== check /llama.cpp inside candidate images ==="
for I in strata-gfx906:0.2.9-101 strata-gfx906:0.2.9 gfx029-build:latest; do
  echo "-- $I"
  docker run --rm "$I" bash -lc 'ls -d /llama.cpp 2>/dev/null; ls /llama.cpp/ggml/include/ggml.h 2>/dev/null' 2>&1 | head -3
done
echo "=== how did build dir get /llama.cpp? grep history ==="
grep -rn "llama.cpp" /home/albus/strata166/data/*.sh 2>/dev/null | head -5
ls /home/albus/*.sh 2>/dev/null | head
