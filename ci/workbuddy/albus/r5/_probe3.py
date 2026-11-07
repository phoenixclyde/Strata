import subprocess, base64
def sh(s, t=120):
    p = subprocess.run(["ssh","-o","BatchMode=yes","-o","ConnectTimeout=10","albus@192.168.50.166","base64 -d | bash"],
                       input=base64.b64encode(s.encode()), stdout=subprocess.PIPE, stderr=subprocess.STDOUT, timeout=t)
    return p.stdout.decode("utf-8","replace")
print(sh(r'''
docker exec strata166-407 bash -lc 'wc -l /src/build-906/CMakeCache.txt; grep -ci roc /src/build-906/CMakeCache.txt; grep -i -m8 "roc" /src/build-906/CMakeCache.txt'
echo "=== hip_backend in image ==="
docker exec strata166-407 bash -lc 'grep -n "STRATA_ROCBLAS_AVAILABLE" /src/cmake/hip_backend.cmake'
echo "=== hipblas version ==="
docker exec strata166-407 bash -lc 'grep -i -m5 "hipblas_VERSION\|HIPBLAS_VERSION" /src/build-906/CMakeCache.txt; ls /opt/rocm/lib/cmake/hipblas/ | head'
echo "=== rocblas config requires ==="
docker exec strata166-407 bash -lc 'head -30 /opt/rocm/lib/cmake/rocblas/rocblas-config.cmake'
'''))
