import subprocess, base64
def sh(s, t=600):
    p = subprocess.run(["ssh","-o","BatchMode=yes","-o","ConnectTimeout=10","albus@192.168.50.166","base64 -d | bash"],
                       input=base64.b64encode(s.encode()), stdout=subprocess.PIPE, stderr=subprocess.STDOUT, timeout=t)
    return p.stdout.decode("utf-8","replace")
print(sh(r'''
docker run --rm --entrypoint bash strata-gfx906:0.2.4p4 -c '
ls -l /tmp/gfx906.o
echo "=== head notes ==="
head -30 /tmp/notes.txt
echo "=== count name: ==="
grep -c "  .name:" /tmp/notes.txt || true
echo "=== strings mul_mat_q ==="
strings /tmp/gfx906.o | grep -c "mul_mat_q" || true
echo "=== elfs in bundle? ==="
/opt/rocm/llvm/bin/clang-offload-bundler -list -type=o -inputs=/tmp/fat.bin 2>&1 | head -5
' 2>&1 | head -45
''', t=600))
