import subprocess, base64
def sh(s, t=30):
    p = subprocess.run(["ssh","-o","BatchMode=yes","-o","ConnectTimeout=10","albus@192.168.50.166","base64 -d | bash"],
                       input=base64.b64encode(s.encode()), stdout=subprocess.PIPE, stderr=subprocess.STDOUT, timeout=t)
    return p.stdout.decode("utf-8","replace")
try:
    print(sh("cd /home/albus/strata166/build024 && setsid nohup docker build -f Dockerfile-0.2.4.p3 -t strata-gfx906:0.2.4p3 . > /tmp/build_p3b.log 2>&1 </dev/null & echo BUILD_STARTED", t=20))
except subprocess.TimeoutExpired:
    print("BUILD_STARTED (channel held)")
