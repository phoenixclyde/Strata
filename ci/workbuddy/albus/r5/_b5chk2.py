import subprocess, base64
def sh(s, t=120):
    p = subprocess.run(["ssh","-o","BatchMode=yes","-o","ConnectTimeout=10","albus@192.168.50.166","base64 -d | bash"],
                       input=base64.b64encode(s.encode()), stdout=subprocess.PIPE, stderr=subprocess.STDOUT, timeout=t)
    return p.stdout.decode("utf-8","replace")
print(sh(r'''
docker images | grep -E "0.2.4p5|0.2.4p4" | head -4
echo "=== tail ==="
tail -12 /tmp/build_p5.log | sed 's/^#1[0-9] //' | cut -c1-190
echo "=== mmq tile lines in build log ==="
grep -a "MMQ tile\|rocblas wired\|max-ilp in flags" /tmp/build_p5.log | tail -3 | cut -c1-160
'''))
