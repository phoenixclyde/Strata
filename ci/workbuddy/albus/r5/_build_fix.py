import subprocess, base64
def sh(s, t=180):
    p = subprocess.run(["ssh","-o","BatchMode=yes","-o","ConnectTimeout=10","albus@192.168.50.166","base64 -d | bash"],
                       input=base64.b64encode(s.encode()), stdout=subprocess.PIPE, stderr=subprocess.STDOUT, timeout=t)
    return p.stdout.decode("utf-8","replace")
print(sh("docker ps --format '{{.Names}} {{.Image}}' | head -3; tail -5 /tmp/build_p3.log 2>/dev/null"))
raw = open(r"D:/workbuddy_space/strata_ws/deploy/docker/patch_gfx906_rocblas.py","rb").read()
pl = base64.b64encode(raw).decode("ascii")
print(sh("echo '%s' | base64 -d > /home/albus/strata166/build024/patches/patch_gfx906_rocblas.py && md5sum /home/albus/strata166/build024/patches/patch_gfx906_rocblas.py" % pl))
print(sh("rm -rf /tmp/pt && mkdir -p /tmp/pt && cp /home/albus/strata166/build024/patches/patch_gfx906_rocblas.py /tmp/pt/ && cp /home/albus/strata166/build024/src/CMakeLists.txt /tmp/pt/CMakeLists.txt && python3 /tmp/pt/patch_gfx906_rocblas.py /tmp/pt/CMakeLists.txt && sed -n '168,180p' /tmp/pt/CMakeLists.txt && grep -n 'OR STRATA_HIP_GFX906) AND STRATA_ROCBLAS_AVAILABLE' /tmp/pt/CMakeLists.txt"))
