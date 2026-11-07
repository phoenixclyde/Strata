import subprocess, base64
def sh(s, t=180):
    p = subprocess.run(["ssh","-o","BatchMode=yes","-o","ConnectTimeout=10","albus@192.168.50.166","base64 -d | bash"],
                       input=base64.b64encode(s.encode()), stdout=subprocess.PIPE, stderr=subprocess.STDOUT, timeout=t)
    return p.stdout.decode("utf-8","replace")
print(sh(r'''
docker run --rm --entrypoint bash strata-gfx906:0.2.4p4 -c '
echo "=== cuda_runtime.h 是否存在 ==="
find /opt/rocm /src -name "cuda_runtime.h" 2>/dev/null | head -5
echo "=== tests 是否参与构建 ==="
grep -c "tests/hip" /src/build-906/build.ninja 2>/dev/null
ninja -C /src/build-906 -t targets all 2>/dev/null | grep -iE "gdn_rec_head|prefill_mmq_parity" | head -5
echo "=== kernels.hpp 存在 ==="
ls /src/include/strata/prefill/kernels.hpp
' 2>&1 | head -20
'''))
