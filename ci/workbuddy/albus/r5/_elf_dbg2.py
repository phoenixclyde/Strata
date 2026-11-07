import subprocess, base64
def sh(s, t=900):
    p = subprocess.run(["ssh","-o","BatchMode=yes","-o","ConnectTimeout=10","albus@192.168.50.166","base64 -d | bash"],
                       input=base64.b64encode(s.encode()), stdout=subprocess.PIPE, stderr=subprocess.STDOUT, timeout=t)
    return p.stdout.decode("utf-8","replace")
print(sh(r'''
docker run --rm --entrypoint bash strata-gfx906:0.2.4p4 -c '
cd /tmp
/opt/rocm/llvm/bin/llvm-objcopy --dump-section .hip_fatbin=/tmp/fat.bin /src/build-906/strata
ls -l /tmp/fat.bin
echo "=== bundle targets ==="
/opt/rocm/llvm/bin/clang-offload-bundler -list -type=o -input=/tmp/fat.bin 2>&1 | head -8
echo "=== unbundle all ==="
/opt/rocm/llvm/bin/clang-offload-bundler -unbundle -type=o -targets=hipv4-amdgcn-amd-amdhsa--gfx906 -input=/tmp/fat.bin -output=/tmp/g906.o 2>&1 | head -4
ls -l /tmp/g906.o 2>&1
/opt/rocm/llvm/bin/llvm-readobj --notes /tmp/g906.o 2>/dev/null | wc -l
/opt/rocm/llvm/bin/llvm-readobj --notes /tmp/g906.o 2>/dev/null | grep -c "amdhsa.kernels"
' 2>&1 | head -25
''', t=900))
