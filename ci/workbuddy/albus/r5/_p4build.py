import subprocess, base64
def sh(s, t=25):
    p = subprocess.run(["ssh","-o","BatchMode=yes","-o","ConnectTimeout=10","albus@192.168.50.166","base64 -d | bash"],
                       input=base64.b64encode(s.encode()), stdout=subprocess.PIPE, stderr=subprocess.STDOUT, timeout=t)
    return p.stdout.decode("utf-8","replace")
try:
    print(sh("cd /home/albus/strata166/build024 && setsid nohup docker build -f Dockerfile-0.2.4.p4 -t strata-gfx906:0.2.4p4 . > /tmp/build_p4.log 2>&1 </dev/null & echo BUILD_STARTED", t=18))
except subprocess.TimeoutExpired:
    print("BUILD_STARTED (held)")
