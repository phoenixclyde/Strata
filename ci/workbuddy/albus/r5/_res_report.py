import subprocess, base64
def sh(s, t=900):
    p = subprocess.run(["ssh","-o","BatchMode=yes","-o","ConnectTimeout=10","albus@192.168.50.166","base64 -d | bash"],
                       input=base64.b64encode(s.encode()), stdout=subprocess.PIPE, stderr=subprocess.STDOUT, timeout=t)
    return p.stdout.decode("utf-8","replace")
print(sh(r'''
docker run --rm --entrypoint bash strata-gfx906:0.2.4p4 -c '
cd /src/build-906
ninja -t commands 2>/dev/null | grep -i "mmq-instance-iq3_s" | head -2 | cut -c1-400
echo "=== targets with iq3_s ==="
ls /src/third_party/llama.cpp/ggml/src/ggml-cuda/template-instances/ 2>/dev/null | grep -E "iq3_s|iq4_nl" | head
' 2>&1 | head -12
''', t=600))
