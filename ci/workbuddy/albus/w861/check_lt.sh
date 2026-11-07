set +e
C=strata166-407
echo "=== rocblas ver ==="
docker exec $C bash -lc 'ls -l /opt/rocm/lib/librocblas* 2>/dev/null | head'
echo "=== hipblaslt backend linked? ==="
docker exec $C bash -lc 'ldd /opt/rocm/lib/librocblas.so.4 2>/dev/null | grep -i -E "hipblaslt|tensile"'
echo "=== symbol check ==="
docker exec $C bash -lc 'nm -D --defined-only /opt/rocm/lib/librocblas.so.4 2>/dev/null | grep -ci hipblaslt; strings /opt/rocm/lib/librocblas.so.4 | grep -c ROCBLAS_USE_HIPBLASLT'
echo "=== strings hit sample ==="
docker exec $C bash -lc 'strings /opt/rocm/lib/librocblas.so.4 | grep -i -E "ROCBLAS_USE_HIPBLASLT|hipblaslt" | sort -u | head -20'
echo "=== hipblaslt lib present ==="
docker exec $C bash -lc 'ls -d /opt/rocm/lib/hipblaslt 2>/dev/null && ls /opt/rocm/lib/hipblaslt/library/ 2>/dev/null | head -20'
echo "=== hipblaslt .so ==="
docker exec $C bash -lc 'ls -l /opt/rocm/lib/libhipblaslt* 2>/dev/null'
echo "=== rocblas library dirs ==="
docker exec $C bash -lc 'ls /opt/rocm/lib/rocblas/library/ 2>/dev/null | head -20; ls -d /opt/rocm/lib/rocblas/library/*gfx906* 2>/dev/null'
