import subprocess, base64
def sh(s, t=90):
    p = subprocess.run(["ssh","-o","BatchMode=yes","-o","ConnectTimeout=10","albus@192.168.50.166","base64 -d | bash"],
                       input=base64.b64encode(s.encode()), stdout=subprocess.PIPE, stderr=subprocess.STDOUT, timeout=t)
    return p.stdout.decode("utf-8","replace")
print(sh(r'''
tail -6 /tmp/build_p3b.log 2>/dev/null | cut -c1-160
echo "=== docker build running? ==="
ps -ef | grep -c "[d]ocker build"
echo "=== time ==="; date +%H:%M:%S
'''))
