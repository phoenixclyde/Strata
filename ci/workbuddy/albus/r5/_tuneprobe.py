import subprocess, base64
def sh(s, t=90):
    p = subprocess.run(["ssh","-o","BatchMode=yes","-o","ConnectTimeout=10","albus@192.168.50.166","base64 -d | bash"],
                       input=base64.b64encode(s.encode()), stdout=subprocess.PIPE, stderr=subprocess.STDOUT, timeout=t)
    return p.stdout.decode("utf-8","replace")
print(sh(r'''
echo "=== src tree on 166 ==="
ls -d /home/albus/strata166/build024/src 2>/dev/null && ls /home/albus/strata166/build024/src/tools/hip/tune_rocblas.cpp 2>/dev/null
echo "=== hipcc / clang ==="
ls -l /opt/rocm/bin/hipcc 2>/dev/null; /opt/rocm/bin/hipcc --version 2>/dev/null | head -3
echo "=== rocblas headers ==="
ls /opt/rocm/include/rocblas/rocblas.h 2>/dev/null; ls /opt/rocm/include/rocblas 2>/dev/null | head -5
echo "=== libs ==="
ls /opt/rocm/lib/librocblas.so* 2>/dev/null | head -3
echo "=== vram ==="
/opt/rocm/bin/rocm-smi --showmeminfo vram 2>/dev/null | grep -E "Total|Used" | head -4
echo "=== host mem ==="
grep -E "^(MemTotal|MemAvailable)" /proc/meminfo
'''))
