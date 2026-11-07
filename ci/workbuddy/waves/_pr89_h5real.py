import os, io, re

SRC = r"D:/strata166/tmp/src402/Strata-0.1.40.2"

print("=== [1] 找 moe_mmq / mmq-instance 相关文件 ===")
hits = []
for dp, dn, fn in os.walk(SRC):
    for f in fn:
        if re.search(r"moe_mmq|mmq.instance|mmq_", f, re.I):
            p = os.path.join(dp, f)
            hits.append((os.path.relpath(p, SRC).replace("\\", "/"), os.path.getsize(p)))
for h, s in sorted(hits):
    print("  %-58s %9d" % (h, s))
if not hits:
    print("  (none)")

print()
print("=== [2] 全树找 GGML_TYPE_Q6_K 的调用点 ===")
for dp, dn, fn in os.walk(SRC):
    for f in fn:
        if not f.endswith((".cu", ".cuh", ".cpp", ".h", ".hpp")):
            continue
        p = os.path.join(dp, f)
        try:
            t = io.open(p, encoding="utf-8", errors="replace").read()
        except Exception:
            continue
        if "GGML_TYPE_Q6_K" not in t:
            continue
        rel = os.path.relpath(p, SRC).replace("\\", "/")
        L = t.split("\n")
        for i, l in enumerate(L):
            if "GGML_TYPE_Q6_K" in l:
                print("  ### %s : %d" % (rel, i + 1))
                for j in range(max(0, i - 8), min(len(L), i + 3)):
                    print("     %5d| %s" % (j + 1, L[j][:126]))
                print("     ----")

print()
print("=== [3] 全树找 __HIPCC__ 与 STRATA_Q6K_EXPERTS 的联合门 ===")
pat = re.compile(r"#if.*(?:__HIPCC__|STRATA_Q6K_EXPERTS|STRATA_HIP_GFX906)")
for dp, dn, fn in os.walk(SRC):
    for f in fn:
        if not f.endswith((".cu", ".cuh", ".cpp", ".h", ".hpp")):
            continue
        p = os.path.join(dp, f)
        try:
            t = io.open(p, encoding="utf-8", errors="replace").read()
        except Exception:
            continue
        rel = os.path.relpath(p, SRC).replace("\\", "/")
        for i, l in enumerate(t.split("\n")):
            if pat.search(l) and ("Q6K" in l or "Q6_K" in l or "q6_k" in l):
                print("  %-52s :%-6d %s" % (rel, i + 1, l.strip()[:110]))

print()
print("=== [4] CMakeLists.txt 里 strata_mmq 的 q6_k 门（前后 12 行）===")
cm = io.open(os.path.join(SRC, "CMakeLists.txt"), encoding="utf-8", errors="replace").read()
L = cm.split("\n")
for i, l in enumerate(L):
    if "_strata_mmq_cuda_types" in l or "_strata_mmq_hip_types" in l:
        for j in range(max(0, i - 3), min(len(L), i + 8)):
            print("  %6d| %s" % (j + 1, L[j][:124]))
        print("  ----")

print()
print("=== [5] 判据汇总 ===")
q6k_call = []
for dp, dn, fn in os.walk(SRC):
    for f in fn:
        if f.endswith((".cu", ".cuh")):
            p = os.path.join(dp, f)
            t = io.open(p, encoding="utf-8", errors="replace").read()
            if "mul_mat_q_case" in t and "Q6_K" in t:
                q6k_call.append(os.path.relpath(p, SRC).replace("\\", "/"))
print("  含 mul_mat_q_case + Q6_K 的文件 =", q6k_call)
print("  CMakeLists 含 'STRATA_Q6K_EXPERTS OR STRATA_HIP_GFX906' =",
      "STRATA_Q6K_EXPERTS OR STRATA_HIP_GFX906" in cm)
