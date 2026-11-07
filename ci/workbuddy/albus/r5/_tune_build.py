import subprocess, base64
HOST="albus@192.168.50.166"
def sh(s, t=300):
    p = subprocess.run(["ssh","-o","BatchMode=yes","-o","ConnectTimeout=10",HOST,"base64 -d | bash"],
                       input=base64.b64encode(s.encode()), stdout=subprocess.PIPE, stderr=subprocess.STDOUT, timeout=t)
    return p.stdout.decode("utf-8","replace")
src = open(r"D:/workbuddy_space/strata_ws/deploy/tmp/_src/s024/tools/hip/tune_rocblas.cpp","rb").read()
pl = base64.b64encode(src).decode("ascii")
print(sh("mkdir -p /home/albus/strata166/tmp/tune && echo '%s' | base64 -d > /home/albus/strata166/tmp/tune/tune_rocblas.cpp && md5sum /home/albus/strata166/tmp/tune/tune_rocblas.cpp && wc -l /home/albus/strata166/tmp/tune/tune_rocblas.cpp" % pl, t=120))
print(sh("cd /home/albus/strata166/tmp/tune && time /opt/rocm/bin/hipcc --offload-arch=gfx906 -O3 -std=c++17 tune_rocblas.cpp -o tune_rocblas -lrocblas 2>&1 | tail -20; ls -l tune_rocblas 2>&1", t=600))
print(sh("cd /home/albus/strata166/tmp/tune && ./tune_rocblas --help 2>&1 | head -5", t=120))
