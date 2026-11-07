import subprocess, base64
CTX="/home/albus/strata166/build024"
def sh(s, t=120):
    p = subprocess.run(["ssh","-o","BatchMode=yes","-o","ConnectTimeout=10","albus@192.168.50.166","base64 -d | bash"],
                       input=base64.b64encode(s.encode()), stdout=subprocess.PIPE, stderr=subprocess.STDOUT, timeout=t)
    return p.stdout.decode("utf-8","replace")
for loc, remote in [("D:/workbuddy_space/strata_ws/deploy/docker/Dockerfile-0.2.4.p4", CTX+"/Dockerfile-0.2.4.p4"),
                    ("D:/workbuddy_space/strata_ws/deploy/docker/patch_gfx906_attn_swizzle.py", CTX+"/patches/patch_gfx906_attn_swizzle.py")]:
    raw=open(loc,"rb").read(); pl=base64.b64encode(raw).decode("ascii")
    print(sh("echo '%s' | base64 -d > %s && wc -c %s" % (pl, remote, remote)).strip())
print(sh(r'''rm -rf /tmp/pt4 && mkdir -p /tmp/pt4 && cp /home/albus/strata166/build024/patches/patch_gfx906_attn_swizzle.py /tmp/pt4/ && cp /home/albus/strata166/build024/src/src/kernels/cuda/qsa_decode_attn.cu /tmp/pt4/ && cd /tmp/pt4 && python3 patch_gfx906_attn_swizzle.py qsa_decode_attn.cu && grep -c "W794" qsa_decode_attn.cu && grep -c "attn_chunk_kernel<3, false, true>" qsa_decode_attn.cu && grep -c "attn_chunk_kernel<3, false, true, true>" qsa_decode_attn.cu && grep -n "kv_mode == 1 || kv_mode == 3" qsa_decode_attn.cu | head -2'''))
