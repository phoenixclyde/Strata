set +e
C=strata166-407
echo "=== full arch list in libhipblaslt ==="
docker exec $C bash -lc 'strings /opt/rocm/lib/libhipblaslt.so.1 | grep -oE "^gfx[0-9a-f]+$" | sort -u'
echo "=== does so mention gfx906 at all ==="
docker exec $C bash -lc 'strings /opt/rocm/lib/libhipblaslt.so.1 | grep -c gfx906'
echo "=== rocblas library gfx906 files ==="
docker exec $C bash -lc 'ls /opt/rocm/lib/rocblas/library/gfx906 | head -8; ls /opt/rocm/lib/rocblas/library/gfx906 | wc -l'
echo "=== src tree ==="
ls -d /home/albus/strata166/rocm-libs 2>/dev/null || docker exec $C bash -lc 'ls -d /src 2>/dev/null'
ls /home/albus/strata166/rocm-libs 2>/dev/null | head
echo "=== hipblaslt src ==="
ls /home/albus/strata166/rocm-libs/projects/hipblaslt 2>/dev/null | head
echo "=== invoke? ==="
docker exec $C bash -lc 'python3 -c "import invoke" 2>&1 | tail -1'
echo "=== pip index test ==="
docker exec $C bash -lc 'timeout 25 pip3 download --no-deps -d /tmp/x invoke -i https://mirrors.aliyun.com/pypi/simple/ 2>&1 | tail -3'
