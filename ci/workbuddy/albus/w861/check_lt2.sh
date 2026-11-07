set +e
C=strata166-407
echo "=== ldd rocblas ==="
docker exec $C bash -lc 'ldd /opt/rocm/lib/librocblas.so.5 | grep -i -E "hipblaslt|tensile|amdhip"'
echo "=== strings USE_HIPBLASLT ==="
docker exec $C bash -lc 'strings /opt/rocm/lib/librocblas.so.5 | grep -i "USE_HIPBLASLT" | sort -u | head'
echo "=== strings hipblaslt count ==="
docker exec $C bash -lc 'strings /opt/rocm/lib/librocblas.so.5 | grep -ci hipblaslt'
echo "=== sample ==="
docker exec $C bash -lc 'strings /opt/rocm/lib/librocblas.so.5 | grep -i hipblaslt | sort -u | head -15'
echo "=== hipblaslt device lib dirs anywhere ==="
docker exec $C bash -lc 'find /opt/rocm -maxdepth 4 -name "TensileLibrary_lazy*" 2>/dev/null | head; ls /opt/rocm/lib/hipblaslt 2>&1 | head'
echo "=== hipblaslt arch whitelist in so ==="
docker exec $C bash -lc 'strings /opt/rocm/lib/libhipblaslt.so.1 | grep -oE "gfx[0-9a-z]+" | sort -u | head -20'
echo "=== env of prod container ==="
docker exec $C bash -lc 'env | grep -i -E "hipblaslt|tensile|rocblas" | head'
