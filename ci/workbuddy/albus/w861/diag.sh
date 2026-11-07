set +e
echo "=== TCL full log head ==="
head -40 /home/albus/strata166/data/w861_tcl1.out 2>/dev/null
echo "=== TCL err lines ==="
grep -nE "Error|error|assert|Assert|WARNING|Reject|reject" /home/albus/strata166/data/w861_tcl1.out 2>/dev/null | head -20
echo "=== GR full log ==="
head -30 /home/albus/strata166/data/w861_gr_build.log 2>/dev/null
echo "=== libstrata_kernels ==="
ls -la /home/albus/strata166/gfx029-build/libstrata* 2>/dev/null
find /home/albus/strata166/gfx029-build -maxdepth 2 -name "*.a" 2>/dev/null | head
echo "=== ninja explain (dry) ==="
docker run --rm -v /home/albus/strata166/gfx029:/src -v /home/albus/strata166/gfx029-build:/out strata-gfx906:0.2.9-101 bash -lc 'cd /out && ninja -d explain -n fused_gr_bench 2>&1 | head -12' 2>&1 | tail -14
