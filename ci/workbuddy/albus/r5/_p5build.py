import subprocess, base64
CTX="/home/albus/strata166/build024"
def sh(s, t=180):
    p = subprocess.run(["ssh","-o","BatchMode=yes","-o","ConnectTimeout=10","albus@192.168.50.166","base64 -d | bash"],
                       input=base64.b64encode(s.encode()), stdout=subprocess.PIPE, stderr=subprocess.STDOUT, timeout=t)
    return p.stdout.decode("utf-8","replace")
for loc, remote in [("D:/workbuddy_space/strata_ws/deploy/docker/Dockerfile-0.2.4.p5", CTX+"/Dockerfile-0.2.4.p5"),
                    ("D:/workbuddy_space/strata_ws/deploy/docker/patch_mmq_tile_j.py", CTX+"/patches/patch_mmq_tile_j.py")]:
    raw=open(loc,"rb").read(); pl=base64.b64encode(raw).decode("ascii")
    print(sh("echo '%s' | base64 -d > %s && wc -c %s" % (pl, remote, remote)).strip())
# 干跑：在副本上验证补丁（不碰构建树）
print(sh(r'''rm -rf /tmp/pt5 && mkdir -p /tmp/pt5 && cp /home/albus/strata166/build024/patches/patch_mmq_tile_j.py /tmp/pt5/ && cp /home/albus/strata166/build024/src/third_party/llama.cpp/ggml/src/ggml-cuda/mmq.cuh /tmp/pt5/ && cd /tmp/pt5 && python3 patch_mmq_tile_j.py mmq.cuh && grep -c "W795" mmq.cuh && grep -c "STRATA_MMQ_TILE_J" mmq.cuh && sed -n '/const int j_cap/,+4p' mmq.cuh'''))
