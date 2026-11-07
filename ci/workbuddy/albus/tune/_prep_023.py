import subprocess, base64, os, hashlib

HOST = "albus@192.168.50.166"
TP = r"D:/workbuddy_space/strata_ws/deploy/tmp/_tpatch"


def run(script, timeout=900):
    b64 = base64.b64encode(script.encode()).decode("ascii")
    p = subprocess.run(["ssh", "-o", "BatchMode=yes", "-o", "ServerAliveInterval=15", HOST, "base64 -d | bash"],
                       input=b64.encode("ascii"), stdout=subprocess.PIPE, stderr=subprocess.STDOUT, timeout=timeout)
    return p.stdout.decode("utf-8", "replace")


# 1) llama.cpp（pin 3cf03257，与 0.2.2 同一棵树）+ patches
print(run(r'''
set -e
cd /home/albus/strata166/build023
mkdir -p patches
if [ ! -d src/third_party/llama.cpp ]; then
  cp -a /home/albus/strata166/build022/src/third_party/llama.cpp src/third_party/llama.cpp
fi
du -sh src/third_party/llama.cpp
test -f src/third_party/llama.cpp/ggml/CMakeLists.txt && echo LLAMA_OK
cat src/third_party/ggml/VERSION.txt
'''))

# 2) 推两个 patched 文件
for nm, local in (("serve-telemetry.py", "serve-telemetry.py.patched.023"),
                  ("serve-web-app.js", "serve-web-app.js.patched.023")):
    data = open(os.path.join(TP, local), "rb").read()
    b64 = base64.b64encode(data).decode("ascii")
    s = "cd /home/albus/strata166/build023 && echo '%s' | base64 -d > patches/%s && md5sum patches/%s && wc -c patches/%s" % (
        b64, nm, nm, nm)
    o = run(s)
    print("[%s] want=%s | %s" % (nm, hashlib.md5(data).hexdigest()[:8], o.replace("\n", " ")))
