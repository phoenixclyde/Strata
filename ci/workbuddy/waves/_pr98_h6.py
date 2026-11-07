import os, io, re

SRC = r"D:/strata166/tmp/src402/Strata-0.1.40.2"

print("=== [1] prefill.cpp:399 附近（失败点）===")
p = os.path.join(SRC, "src", "prefill", "prefill.cpp")
t = io.open(p, encoding="utf-8", errors="replace").read()
L = t.split("\n")
for j in range(388, 410):
    mark = "   <== ERROR" if j + 1 == 399 else ""
    print("  %5d| %s%s" % (j + 1, L[j][:126], mark))

print()
print("=== [2] 全树里 cudaEventBlockingSync 的出现 ===")
for dp, dn, fn in os.walk(SRC):
    if "sycl" in dp:
        continue
    for f in fn:
        if not f.endswith((".cu", ".cuh", ".cpp", ".h", ".hpp")):
            continue
        fp = os.path.join(dp, f)
        try:
            s = io.open(fp, encoding="utf-8", errors="replace").read()
        except Exception:
            continue
        if "cudaEventBlockingSync" in s:
            rel = os.path.relpath(fp, SRC).replace("\\", "/")
            for i, l in enumerate(s.split("\n")):
                if "cudaEventBlockingSync" in l:
                    print("  %-46s :%-5d %s" % (rel, i + 1, l.strip()[:110]))

print()
print("=== [3] strata_hip.h 里现有的 cudaEvent* 映射 ===")
H = os.path.join(SRC, "include", "strata", "platform", "hip_compat", "strata_hip.h")
h = io.open(H, encoding="utf-8", errors="replace").read()
HL = h.split("\n")
for i, l in enumerate(HL):
    if "cudaEvent" in l or "hipEvent" in l:
        print("  %5d| %s" % (i + 1, l[:126]))

print()
print("=== [4] 该头文件里 cudaStreamCreateWithFlags 那几行（找插入锚点）===")
for i, l in enumerate(HL):
    if "cudaStreamCreateWithFlags" in l or "cudaStreamSynchronize" in l or "hipEventBlockingSync" in l:
        print("  %5d| %s" % (i + 1, l[:126]))

print()
print("=== [5] prefill.cpp 是否被 gfx906 gate ===")
for i, l in enumerate(L[:60]):
    if "STRATA_HIP_GFX906" in l or "STRATA_USE_HIP" in l:
        print("  %5d| %s" % (i + 1, l[:126]))
print("  全文 STRATA_HIP_GFX906 命中 =", t.count("STRATA_HIP_GFX906"),
      " STRATA_USE_HIP 命中 =", t.count("STRATA_USE_HIP"))
