#!/usr/bin/env python3
"""W1039: apply the b12110 API delta to pr/port-all so it builds against the b12180 llama tree.

Same three adaptations that pr/k10 needed (k10_api_fix2.py / k10_api_fix3.py), re-applied here because
port-all is a separate worktree: it still targets pin b11062.
  (a) mul_mat_q_case<type>(...) -> mul_mat_q_case<type, GGML_PREC_Q8>(...)
  (b) ggml_cuda_mmq_get_config(type, J, fallback, cc) -> (..., GGML_PREC_Q8)
  (c) new_pool_for_device(int, int) -> new_pool_for_device(ctx &, int, int)
"""
import io
import os
import re
import shutil
import subprocess

WT = "/home/albus/strata166/pr/port-all"
SRC = os.path.join(WT, "src")

# (a)
pat = re.compile(r"(mul_mat_q_case<GGML_TYPE_[A-Z0-9_]+)(>\(\s*ctx)")
total = 0
for root, _, files in os.walk(SRC):
    for fn in files:
        if not fn.endswith((".cu", ".cuh")):
            continue
        p = os.path.join(root, fn)
        s = io.open(p, encoding="utf-8", errors="replace").read()
        if "GGML_PREC_Q8" in s and not pat.search(s):
            continue
        t, n = pat.subn(r"\1, GGML_PREC_Q8\2", s)
        if n:
            shutil.copy2(p, p + ".bak_pa3")
            io.open(p, "w", encoding="utf-8", newline="\n").write(t)
            total += n
            print("%-46s %d" % (os.path.relpath(p, WT), n))
print("(a) mul_mat_q_case call sites patched:", total)

# (b)
p = os.path.join(WT, "src/prefill/moe_mmq.cu")
s = io.open(p, encoding="utf-8").read()
out, n = [], 0
for ln in s.split("\n"):
    if "ggml_cuda_mmq_get_config(" in ln and "GGML_PREC_Q8" not in ln:
        t = ln.replace(", info.devices[id].cc);", ", info.devices[id].cc, GGML_PREC_Q8);")
        if t == ln:
            t = ln.replace(", cc);", ", cc, GGML_PREC_Q8);")
        if t != ln:
            n += 1
        out.append(t)
    else:
        out.append(ln)
if n:
    io.open(p, "w", encoding="utf-8", newline="\n").write("\n".join(out))
print("(b) moe_mmq.cu get_config patched:", n)

# (c)
p2 = os.path.join(WT, "src/prefill/ggml_cuda_host.cu")
s2 = io.open(p2, encoding="utf-8").read()
OLD = "ggml_backend_cuda_context::new_pool_for_device(int, int) {"
NEW = "ggml_backend_cuda_context::new_pool_for_device(ggml_backend_cuda_context &, int, int) {"
if NEW in s2:
    print("(c) already patched")
elif OLD in s2:
    shutil.copy2(p2, p2 + ".bak_pa3")
    io.open(p2, "w", encoding="utf-8", newline="\n").write(s2.replace(OLD, NEW, 1))
    print("(c) new_pool_for_device patched")
else:
    print("(c) WARN anchor missing")

print("--- leftovers ---")
r = subprocess.run("grep -rn 'mul_mat_q_case<GGML_TYPE_[A-Z0-9_]*>(' %s --include=*.cu --include=*.cuh | wc -l" % SRC,
                   shell=True, capture_output=True, text=True)
print("1-arg mul_mat_q_case:", r.stdout.strip())
r = subprocess.run("grep -rn 'ggml_cuda_mmq_get_config(' %s | grep -v GGML_PREC_Q8 | grep -v 'mmq.cuh'" % SRC,
                   shell=True, capture_output=True, text=True)
print("get_config without prec:", (r.stdout.strip() or "none"))
