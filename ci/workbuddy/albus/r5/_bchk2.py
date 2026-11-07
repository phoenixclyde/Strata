import subprocess, base64
def sh(s, t=90):
    p = subprocess.run(["ssh","-o","BatchMode=yes","-o","ConnectTimeout=10","albus@192.168.50.166","base64 -d | bash"],
                       input=base64.b64encode(s.encode()), stdout=subprocess.PIPE, stderr=subprocess.STDOUT, timeout=t)
    return p.stdout.decode("utf-8","replace")
print(sh(r'''
docker images | grep -E "0.2.4p3|0.2.4 " | head -3
echo "=== log tail 25 ==="
tail -25 /tmp/build_p3b.log | cut -c1-200
echo "=== error lines ==="
grep -a -n -E "ERROR|error:|FAILED|max-ilp|rocblas wired|max-ilp in flags|STRATA_ROCBLAS_AVAILABLE" /tmp/build_p3b.log | tail -12 | cut -c1-220
'''))
