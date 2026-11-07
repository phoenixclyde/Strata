import subprocess, base64
def sh(s, t=120):
    p = subprocess.run(["ssh","-o","BatchMode=yes","-o","ConnectTimeout=10","albus@192.168.50.166","base64 -d | bash"],
                       input=base64.b64encode(s.encode()), stdout=subprocess.PIPE, stderr=subprocess.STDOUT, timeout=t)
    return p.stdout.decode("utf-8","replace")
print(sh(r'''
ls -d /home/albus/strata166/build024 2>/dev/null && ls /home/albus/strata166/build024
echo "=== patches ==="
ls -l /home/albus/strata166/build024/patches 2>/dev/null | head
echo "=== src version ==="
grep -m1 "project(strata VERSION" /home/albus/strata166/build024/src/CMakeLists.txt 2>/dev/null
echo "=== dockerfiles on 166 ==="
ls -l /home/albus/strata166/build024/*.Dockerfile /home/albus/strata166/build024/Dockerfile* 2>/dev/null | head
echo "=== images ==="
docker images | grep strata-gfx906 | head -8
echo "=== disk ==="
df -h /var/lib/docker 2>/dev/null | tail -1
'''))
