import subprocess, base64, hashlib
def sh(s, t=120):
    p = subprocess.run(["ssh","-o","BatchMode=yes","-o","ConnectTimeout=10","albus@192.168.50.166","base64 -d | bash"],
                       input=base64.b64encode(s.encode()), stdout=subprocess.PIPE, stderr=subprocess.STDOUT, timeout=t)
    return p.stdout.decode("utf-8","replace")
loc = open(r"D:/workbuddy_space/strata_ws/deploy/tmp/_src/llm_pin/ggml/src/ggml-cuda/mmq.cuh","rb").read()
print("local md5", hashlib.md5(loc).hexdigest(), len(loc))
print(sh("docker run --rm --entrypoint sh strata-gfx906:0.2.4p4 -c 'md5sum /src/third_party/llama.cpp/ggml/src/ggml-cuda/mmq.cuh; wc -c /src/third_party/llama.cpp/ggml/src/ggml-cuda/mmq.cuh; ls /src/patches 2>/dev/null | head'", t=90))
