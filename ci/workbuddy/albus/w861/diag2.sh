set +e
cd /home/albus/strata166/gfx029-build
echo "=== ninja commands for fused_gr_bench ==="
docker run --rm -v /home/albus/strata166/gfx029:/src -v /home/albus/strata166/gfx029-build:/out strata-gfx906:0.2.9-101 bash -lc 'cd /out && ninja -t commands fused_gr_bench 2>&1 | head -6' 2>&1 | tail -10
echo "=== strata_kernels artifact ==="
find /home/albus/strata166/gfx029-build -maxdepth 3 -name "libstrata_kernels*" 2>/dev/null | head
echo "=== build.ninja mtime vs inputs ==="
ls -la --time-style=full-iso /home/albus/strata166/gfx029-build/build.ninja 2>/dev/null
find /home/albus/strata166/gfx029 -maxdepth 1 -name "CMakeLists.txt" -printf "%T+ %p\n" 2>/dev/null
echo "=== STRATA_GGML_DIR in cmake files ==="
grep -rn "STRATA_GGML_DIR" /home/albus/strata166/gfx029/CMakeLists.txt 2>/dev/null | head -6
