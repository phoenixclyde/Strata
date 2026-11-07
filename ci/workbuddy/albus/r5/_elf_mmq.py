import subprocess, base64
def sh(s, t=600):
    p = subprocess.run(["ssh","-o","BatchMode=yes","-o","ConnectTimeout=10","albus@192.168.50.166","base64 -d | bash"],
                       input=base64.b64encode(s.encode()), stdout=subprocess.PIPE, stderr=subprocess.STDOUT, timeout=t)
    return p.stdout.decode("utf-8","replace")
print(sh(r'''
docker run --rm --entrypoint bash strata-gfx906:0.2.4p4 -c '
set -e
cd /tmp
/opt/rocm/llvm/bin/llvm-objcopy --dump-section .hip_fatbin=/tmp/fat.bin /src/build-906/strata
ls -l /tmp/fat.bin
/opt/rocm/llvm/bin/clang-offload-bundler --unbundle --type=o --targets=hipv4-amdgcn-amd-amdhsa--gfx906 -i /tmp/fat.bin -o /tmp/gfx906.o 2>&1 | tail -3
ls -l /tmp/gfx906.o
/opt/rocm/llvm/bin/llvm-readobj --notes /tmp/gfx906.o 2>/dev/null | grep -c "amdhsa.kernels" || true
' 2>&1 | tail -8
''', t=600))
