import subprocess, base64
def sh(s, t=120):
    p = subprocess.run(["ssh","-o","BatchMode=yes","-o","ConnectTimeout=10","albus@192.168.50.166","base64 -d | bash"],
                       input=base64.b64encode(s.encode()), stdout=subprocess.PIPE, stderr=subprocess.STDOUT, timeout=t)
    return p.stdout.decode("utf-8","replace")
ctx = "/home/albus/strata166/build024"
for loc, remote in [
    ("D:/workbuddy_space/strata_ws/deploy/docker/Dockerfile-0.2.4.p3", ctx + "/Dockerfile-0.2.4.p3"),
    ("D:/workbuddy_space/strata_ws/deploy/docker/patch_gfx906_rocblas.py", ctx + "/patches/patch_gfx906_rocblas.py"),
]:
    raw = open(loc, "rb").read()
    pl = base64.b64encode(raw).decode("ascii")
    o = sh("echo '%s' | base64 -d > %s && wc -c %s" % (pl, remote, remote))
    print(o.strip())
# 干跑：先在副本上验证补丁能打
print(sh("cd %s && cp src/CMakeLists.txt /tmp/cm.bak && mkdir -p /tmp/pt && cp patches/patch_gfx906_rocblas.py /tmp/pt/ && cp src/CMakeLists.txt /tmp/pt/CMakeLists.txt && python3 /tmp/pt/patch_gfx906_rocblas.py /tmp/pt/CMakeLists.txt && grep -n 'W793' /tmp/pt/CMakeLists.txt | head -3 && grep -n 'STRATA_HIP_GFX906) AND STRATA_ROCBLAS_AVAILABLE' /tmp/pt/CMakeLists.txt" % ctx))
try:
    print(sh("cd %s && setsid nohup docker build -f Dockerfile-0.2.4.p3 -t strata-gfx906:0.2.4p3 . > /tmp/build_p3.log 2>&1 </dev/null & echo BUILD_STARTED" % ctx, t=20))
except subprocess.TimeoutExpired:
    print("BUILD_STARTED (channel held)")
