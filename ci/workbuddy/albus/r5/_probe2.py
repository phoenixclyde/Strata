import subprocess, base64
def sh(s, t=120):
    p = subprocess.run(["ssh","-o","BatchMode=yes","-o","ConnectTimeout=10","albus@192.168.50.166","base64 -d | bash"],
                       input=base64.b64encode(s.encode()), stdout=subprocess.PIPE, stderr=subprocess.STDOUT, timeout=t)
    return p.stdout.decode("utf-8","replace")
print(sh(r'''
docker exec strata166-407 sh -lc 'ls /opt/rocm/lib/cmake/ 2>/dev/null | head -20; echo ---; ls /opt/rocm/lib/cmake/rocblas 2>/dev/null; echo ---; dpkg -l 2>/dev/null | grep -E "rocblas|hipblas" | head -10'
echo "=== ninja prefill deps ==="
docker exec strata166-407 sh -lc 'grep -m1 -o "rocblas" /src/build-906/build.ninja | head -2; echo "(empty means not linked)"'
echo "=== configure log ==="
docker exec strata166-407 sh -lc 'ls /src/build-906/CMakeCache.txt && grep -i -E "rocblas|hipblaslt" /src/build-906/CMakeCache.txt | head -10'
'''))
