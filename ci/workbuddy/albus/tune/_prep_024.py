import subprocess, base64, os, hashlib

HOST = "albus@192.168.50.166"
TP = r"D:/workbuddy_space/strata_ws/deploy/tmp/_tpatch"


def run(script, timeout=900):
    b64 = base64.b64encode(script.encode()).decode("ascii")
    p = subprocess.run(["ssh", "-o", "BatchMode=yes", "-o", "ServerAliveInterval=15", HOST, "base64 -d | bash"],
                       input=b64.encode("ascii"), stdout=subprocess.PIPE, stderr=subprocess.STDOUT, timeout=timeout)
    return p.stdout.decode("utf-8", "replace")


# 1) llama.cpp（pin 未变，复用）+ patches（上游文件相同，直接复用 023 移植件）
print(run(r'''
set -e
cd /home/albus/strata166/build024
mkdir -p patches
if [ ! -d src/third_party/llama.cpp ]; then
  cp -a /home/albus/strata166/build023/src/third_party/llama.cpp src/third_party/llama.cpp
fi
du -sh src/third_party/llama.cpp
cat src/third_party/ggml/VERSION.txt
'''))

for nm, local in (("serve-telemetry.py", "serve-telemetry.py.patched.023"),
                  ("serve-web-app.js", "serve-web-app.js.patched.023")):
    data = open(os.path.join(TP, local), "rb").read()
    b64 = base64.b64encode(data).decode("ascii")
    o = run("cd /home/albus/strata166/build024 && echo '%s' | base64 -d > patches/%s && md5sum patches/%s" % (b64, nm, nm))
    print("[%s] want=%s | %s" % (nm, hashlib.md5(data).hexdigest()[:8], o.strip()))

# 2) dflash2 的 gfx906 补丁（该文件与 023 逐字节相同，锚点必然仍在）
print(run(r'''
cd /home/albus/strata166/build024/src
python3 - <<'PY'
import io
p = "CMakeLists.txt"
a = "    src/core/arch_defaults.cpp src/core/nv_defaults.cpp src/core/vmm.cpp src/core/conversation_file.cpp)\n"
patch = a + (
    "\n"
    "  # [W776 local] gfx906 (STRATA_HIP_GFX906) does not define STRATA_USE_HIP, but dflash2.cpp keys its\n"
    "  # CUDA-vs-HIP branches on it (stream priority + the fork default). Scope the definition to that one\n"
    "  # file: a global STRATA_USE_HIP would switch CUDA-only paths elsewhere (W717/P23 measured that).\n"
    "  if(STRATA_HIP_GFX906)\n"
    "    set_source_files_properties(src/core/dflash2.cpp PROPERTIES COMPILE_DEFINITIONS \"STRATA_USE_HIP=1\")\n"
    "  endif()\n"
)
s = io.open(p, encoding="utf-8-sig").read()
n = s.count(a)
print("anchor hits:", n)
if n != 1:
    raise SystemExit("FAIL-CLOSED anchor %d" % n)
if "STRATA_USE_HIP=1" in s:
    print("already patched")
else:
    io.open(p, "w", encoding="utf-8", newline="\n").write(s.replace(a, patch, 1))
    print("patched")
PY
grep -c "STRATA_USE_HIP=1" CMakeLists.txt
'''))
