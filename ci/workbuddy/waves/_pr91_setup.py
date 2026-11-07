import os, io, re

SRC = r"D:/strata166/tmp/src402/Strata-0.1.40.2"

print("=== [1] setup.py 的 LLAMA_CPP_COMMIT 与关键常量 ===")
sp = os.path.join(SRC, "setup.py")
t = io.open(sp, encoding="utf-8", errors="replace").read()
print("  setup.py = %d B / %d lines" % (len(t.encode()), len(t.split("\n"))))
for pat in [r"LLAMA_CPP_COMMIT\s*=\s*['\"]([0-9a-f]{6,40})['\"]",
            r"MIN_ENGINE\s*=\s*['\"]?([0-9.]+)",
            r"VERSION\s*=\s*['\"]([0-9.]+)['\"]"]:
    for m in re.finditer(pat, t):
        print("  %-28s -> %s" % (pat.split("\\")[0][:26], m.group(1)))

print()
print("=== [2] CMakeLists.txt 的 project 版本 ===")
cm = io.open(os.path.join(SRC, "CMakeLists.txt"), encoding="utf-8", errors="replace").read()
m = re.search(r"project\s*\(\s*strata\s+VERSION\s+([0-9.]+)", cm)
print("  project(strata VERSION ...) =", m.group(1) if m else "NOT FOUND")

print()
print("=== [3] 四个开关仍在？ ===")
for k in ["STRATA_HIP_GFX906", "STRATA_ENABLE_CUDA", "STRATA_MMQ_KQUANTS", "STRATA_PREFILL_MMQ"]:
    print("  %-24s in CMakeLists = %s" % (k, k in cm))

print()
print("=== [4] 现有 llama.cpp 依赖包 ===")
TR = r"D:/strata166/transfer"
for f in sorted(os.listdir(TR)):
    print("  %-40s %12d" % (f, os.path.getsize(os.path.join(TR, f))))

print()
print("=== [5] 0.1.40.1 vs 0.1.40.2 的源码 zip 大小 ===")
for f in ["strata-src-0.1.39.zip", "strata-src-0.1.40.1.zip", "strata-src-0.1.40.2.zip"]:
    p = os.path.join(TR, f)
    if os.path.isfile(p):
        print("  %-30s %12d B" % (f, os.path.getsize(p)))
