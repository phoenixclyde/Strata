import subprocess, base64
def sh(s, t=180):
    p = subprocess.run(["ssh","-o","BatchMode=yes","-o","ConnectTimeout=10","albus@192.168.50.166","base64 -d | bash"],
                       input=base64.b64encode(s.encode()), stdout=subprocess.PIPE, stderr=subprocess.STDOUT, timeout=t)
    return p.stdout.decode("utf-8","replace")
print(sh(r'''
docker run --rm --entrypoint bash strata-gfx906:0.2.4p4 -c '
ls /opt/rocm/llvm/bin/ | grep -E "objcopy|readobj|bundler" | head
echo "=== hip libs ==="
find /src/build-906 -name "*ggml*hip*" -o -name "libggml*so" 2>/dev/null | head -8
echo "=== strata binary ==="
ls -l /src/build-906/strata 2>/dev/null
' 2>&1 | head -20
'''))
