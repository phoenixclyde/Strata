import subprocess, base64
def sh(s, t=120):
    p = subprocess.run(["ssh","-o","BatchMode=yes","-o","ConnectTimeout=10","albus@192.168.50.166","base64 -d | bash"],
                       input=base64.b64encode(s.encode()), stdout=subprocess.PIPE, stderr=subprocess.STDOUT, timeout=t)
    return p.stdout.decode("utf-8","replace")
print(sh(r'''
docker images | grep -E "0.2.4p5" | head -2
tail -5 /tmp/build_p5.log | cut -c1-200
echo "=== errors ==="
grep -a -n -E "ERROR|error:|FAILED|W795|patched" /tmp/build_p5.log | tail -6 | cut -c1-200
ps -ef | grep -c "[d]ocker build"
'''))
