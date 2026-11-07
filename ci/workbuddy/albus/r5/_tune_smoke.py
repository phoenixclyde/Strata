import subprocess, base64
def sh(s, t=240):
    p = subprocess.run(["ssh","-o","BatchMode=yes","-o","ConnectTimeout=10","albus@192.168.50.166","base64 -d | bash"],
                       input=base64.b64encode(s.encode()), stdout=subprocess.PIPE, stderr=subprocess.STDOUT, timeout=t)
    return p.stdout.decode("utf-8","replace")
print(sh("cd /home/albus/strata166/tmp/tune && ./tune_rocblas --case 256,512,2560,512 2>&1 | head -20", t=240))
