import os, io, re, sys, shutil, zipfile, hashlib, subprocess

ZIP = r"D:/strata166/transfer/strata-src-0.1.40.2.zip"
TMP = r"D:/strata166/tmp/src402"
PATCHER = r"D:/strata166/docker/patch_gfx906.py"

print("=== [1] 解压 0.1.40.2 源码 ===")
if os.path.isdir(TMP):
    shutil.rmtree(TMP, ignore_errors=True)
os.makedirs(TMP, exist_ok=True)
with zipfile.ZipFile(ZIP) as z:
    z.extractall(TMP)
inner = [d for d in os.listdir(TMP) if os.path.isdir(os.path.join(TMP, d))]
print("  内层目录 =", inner)
SRC = os.path.join(TMP, inner[0]) if len(inner) == 1 else TMP
print("  源码根 =", SRC)
print("  CMakeLists.txt 存在 =", os.path.isfile(os.path.join(SRC, "CMakeLists.txt")))

print()
print("=== [2] H5 的真实判据：moe_mmq.cu 里 q6_k 的调用门 ===")
mm = os.path.join(SRC, "src", "kernels", "cuda", "moe_mmq.cu")
if os.path.isfile(mm):
    t = io.open(mm, encoding="utf-8", errors="replace").read()
    L = t.split("\n")
    for i, l in enumerate(L):
        if "Q6_K" in l or "q6_k" in l:
            for j in range(max(0, i - 6), min(len(L), i + 3)):
                print("  %5d| %s" % (j + 1, L[j][:128]))
            print("  ----")
else:
    print("  ABSENT:", mm)

print()
print("=== [3] 补丁前：关键文件 md5 ===")
KEYS = ["include/strata/platform/hip_compat/strata_hip.h",
        "src/kernels/cuda/fused_gr.cu", "src/core/mtp.cpp", "src/core/vmm.cpp",
        "CMakeLists.txt"]
before = {}
for k in KEYS:
    p = os.path.join(SRC, k)
    if os.path.isfile(p):
        b = open(p, "rb").read()
        before[k] = hashlib.md5(b).hexdigest()
        print("  %-56s %8d  %s" % (k, len(b), before[k][:16]))
    else:
        print("  %-56s ABSENT" % k)

print()
print("=== [4] 跑补丁器（--root 指向 0.1.40.2 树）===")
r = subprocess.run([sys.executable, PATCHER, "--root", SRC],
                   capture_output=True, timeout=300)
print("  rc =", r.returncode)
print(r.stdout.decode("utf-8", "replace"))
if r.stderr.strip():
    print("  --- STDERR ---")
    print(r.stderr.decode("utf-8", "replace")[:1200])

print()
print("=== [5] 补丁后：哪些文件变了 ===")
for k in KEYS:
    p = os.path.join(SRC, k)
    if not os.path.isfile(p):
        continue
    b = open(p, "rb").read()
    a = hashlib.md5(b).hexdigest()
    print("  %-56s %s  %s" % (k, a[:16],
                              "SAME" if a == before.get(k) else "CHANGED"))
