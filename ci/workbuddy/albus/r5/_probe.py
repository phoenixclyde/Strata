import subprocess, base64

def sh(s, t=180):
    p = subprocess.run(["ssh","-o","BatchMode=yes","-o","ConnectTimeout=10","albus@192.168.50.166","base64 -d | bash"],
                       input=base64.b64encode(s.encode()), stdout=subprocess.PIPE, stderr=subprocess.STDOUT, timeout=t)
    return p.stdout.decode("utf-8","replace")

S = r'''
echo "=== rocblas-bench ==="
docker exec strata166-407 sh -lc 'ls /opt/rocm/bin/ | grep -i -E "rocblas|hipblas" ' 2>&1 | head
echo "=== rocblas version ==="
docker exec strata166-407 sh -lc 'ls /opt/rocm/lib/librocblas.so* 2>/dev/null; strings /opt/rocm/lib/librocblas.so.4 2>/dev/null | grep -m3 -E "^[0-9]+\.[0-9]+\.[0-9]+\.?[0-9a-f]*$"' 2>&1 | head -6
echo "=== build defines ==="
docker exec strata166-407 sh -lc 'grep -o -E "STRATA_[A-Z0-9_]+" /src/build-906/CMakeCache.txt 2>/dev/null | sort -u | head -40' 2>&1
echo "=== mmq / hipblaslt / rocblas in compile_commands ==="
docker exec strata166-407 sh -lc 'ls /src/build-906/*.ninja >/dev/null 2>&1 && grep -o -E "STRATA_(PREFILL_MMQ|ROCBLAS_AVAILABLE|HIPBLASLT_AVAILABLE|ENABLE_HIP)[A-Z_]*=1" /src/build-906/build.ninja 2>/dev/null | sort | uniq -c' 2>&1 | head
echo "=== needle tool ==="
docker exec strata166-407 sh -lc 'ls -l /src/tools/needle_bench.py' 2>&1
'''
print(sh(S))
