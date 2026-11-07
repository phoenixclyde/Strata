import os, io, hashlib, re

NEW = r"D:/strata166/upstream/v0.1.40.2"
OLD = r"D:/strata166/upstream/v0.1.40.1"

PAIRS = [
    ("src__kernels__cuda__fused_gr.cu", "src/kernels/cuda/fused_gr.cu"),
    ("src__core__mtp.cpp", "src/core/mtp.cpp"),
    ("src__core__vmm.cpp", "src/core/vmm.cpp"),
    ("include__strata__platform__hip_compat__strata_hip.h",
     "include/strata/platform/hip_compat/strata_hip.h"),
]

print("=== [1] 0.1.40.1 vs 0.1.40.2 逐字节对比 ===")
for nf, path in PAIRS:
    pn = os.path.join(NEW, nf)
    po = os.path.join(OLD, nf)
    bn = open(pn, "rb").read() if os.path.isfile(pn) else None
    bo = open(po, "rb").read() if os.path.isfile(po) else None
    mn = hashlib.md5(bn).hexdigest() if bn else "ABSENT"
    mo = hashlib.md5(bo).hexdigest() if bo else "ABSENT"
    print("  %-52s new=%8s %s" % (path, len(bn) if bn else "-", mn[:16]))
    print("  %-52s old=%8s %s   %s" % ("", len(bo) if bo else "-", mo[:16],
                                       "SAME" if mn == mo else "DIFF"))

def show(tag, text, pat, ctx_before=1, ctx_after=8, limit=6):
    lines = text.split("\n")
    hits = 0
    print("  --- %s ---" % tag)
    for i, l in enumerate(lines):
        if re.search(pat, l):
            hits += 1
            if hits > limit:
                break
            for j in range(max(0, i - ctx_before), min(len(lines), i + ctx_after)):
                print("      %5d| %s" % (j + 1, lines[j][:132]))
            print("      ----")
    if hits == 0:
        print("      (no match for %r)" % pat)
    return hits

print()
print("=== [2] 锚点 H2/H3: mtp.cpp & vmm.cpp 的 `!defined(STRATA_USE_HIP)` ===")
for nf, path in [("src__core__mtp.cpp", "mtp.cpp"), ("src__core__vmm.cpp", "vmm.cpp")]:
    p = os.path.join(NEW, nf)
    if not os.path.isfile(p):
        print("  [%s] ABSENT" % path)
        continue
    t = io.open(p, encoding="utf-8", errors="replace").read()
    print("  ### %s (%d lines)" % (path, len(t.split("\n"))))
    show("!defined(STRATA_USE_HIP)", t, r"!defined\s*\(\s*STRATA_USE_HIP")
    show("STRATA_HIP_GFX906", t, r"STRATA_HIP_GFX906", limit=4)

print()
print("=== [3] 锚点 H1: fused_gr.cu 的 fused_gr_read_multi ===")
p = os.path.join(NEW, "src__kernels__cuda__fused_gr.cu")
t = io.open(p, encoding="utf-8", errors="replace").read()
L = t.split("\n")
for i, l in enumerate(L):
    if "fused_gr_read_multi" in l and ("bool" in l or "return" in l):
        print("      %5d| %s" % (i + 1, l[:132]))
print("  --- STRATA_HIP_GFX906 出现处 ---")
show("gfx906", t, r"STRATA_HIP_GFX906", limit=6)

print()
print("=== [4] 结论判据 ===")
mtp = io.open(os.path.join(NEW, "src__core__mtp.cpp"), encoding="utf-8", errors="replace").read()
vmm_p = os.path.join(NEW, "src__core__vmm.cpp")
vmm = io.open(vmm_p, encoding="utf-8", errors="replace").read() if os.path.isfile(vmm_p) else ""
fg = io.open(os.path.join(NEW, "src__kernels__cuda__fused_gr.cu"), encoding="utf-8", errors="replace").read()
print("  mtp.cpp   含 '!defined(STRATA_USE_HIP)' 且同行/近行含 GFX906 :",
      bool(re.search(r"!defined\s*\(\s*STRATA_USE_HIP\s*\)[^\n]*GFX906", mtp)))
print("  vmm.cpp   同上                                          :",
      bool(re.search(r"!defined\s*\(\s*STRATA_USE_HIP\s*\)[^\n]*GFX906", vmm)))
print("  fused_gr  含 'return false' 于 gfx906 分支                :",
      "STRATA_HIP_GFX906" in fg and "return false;" in fg)
print("  (以上任一为 False => 该处仍需打补丁)")
