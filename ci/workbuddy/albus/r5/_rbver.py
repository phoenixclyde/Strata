import subprocess, base64
def sh(s, t=120):
    p = subprocess.run(["ssh","-o","BatchMode=yes","-o","ConnectTimeout=10","albus@192.168.50.166","base64 -d | bash"],
                       input=base64.b64encode(s.encode()), stdout=subprocess.PIPE, stderr=subprocess.STDOUT, timeout=t)
    return p.stdout.decode("utf-8","replace")
print(sh(r'''
echo "=== container rocblas version string ==="
docker run --rm --entrypoint sh strata-gfx906:0.2.4 -c 'strings /opt/rocm/lib/librocblas.so.5.5 2>/dev/null | grep -m5 -E "^5\.[0-9]+\.[0-9]+\.[0-9a-f]{6,}"' 2>&1 | head -5
echo "=== host ==="
strings /opt/rocm/lib/librocblas.so.5.5 2>/dev/null | grep -m3 -E "^5\.[0-9]+\.[0-9]+\.[0-9a-f]{6,}" | head -3
echo "=== table head ==="
head -5 /home/albus/strata166/data/gfx906-rocblas-5.5.0.txt
'''))
