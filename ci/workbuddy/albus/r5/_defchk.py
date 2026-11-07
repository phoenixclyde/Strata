import subprocess, base64
def sh(s, t=120):
    p = subprocess.run(["ssh","-o","BatchMode=yes","-o","ConnectTimeout=10","albus@192.168.50.166","base64 -d | bash"],
                       input=base64.b64encode(s.encode()), stdout=subprocess.PIPE, stderr=subprocess.STDOUT, timeout=t)
    return p.stdout.decode("utf-8","replace")
print(sh(r'''
docker run --rm --entrypoint bash strata-gfx906:0.2.4p3 -c '
cd /src/build-906
echo "== gemm.cu compile line has define? =="
grep -c "STRATA_ROCBLAS_AVAILABLE" build.ninja
grep -m2 -o "FLAGS = .*" build.ninja | grep -c ROCBLAS
echo "== which objects carry it =="
grep -o "[a-zA-Z0-9_./-]*\.o: CXX_COMPILER__[a-z_]*" build.ninja | head -3
echo "== prefill objects with define =="
grep -n "STRATA_ROCBLAS_AVAILABLE" build.ninja | head -6 | cut -c1-200
echo "== binary links rocblas? =="
ldd strata | grep -i rocblas
' 2>&1 | head -20
'''))
