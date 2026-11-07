# -*- coding: utf-8 -*-
"""R90-S3 first pass: thread upstream 0.8.0's ggml_prec through our MMQ call sites (branch exp/R90-080).

Three mechanical edits, nothing else:
  1. mul_mat_q_case<T>(  ->  mul_mat_q_case<T, GGML_PREC_Q8>(     (upstream mmq.cu uses PREC_Q8 for these types)
  2. ggml_cuda_mmq_get_config(a, b, c, cc)  ->  (..., cc, GGML_PREC_Q8)
  3. mmq_args init: p.max_rows is int64_t, the struct field is int on 0.8.0 -> cast
Run: python3 port_mmq081.py <worktree>
"""
import io, os, re, sys

W = sys.argv[1]
changed = []

# 1) template precision argument
pat = re.compile(r"(?<!strata_w4a4_)(?<!\w)mul_mat_q_case<([A-Z0-9_]+)>\(")
for root, _, files in os.walk(os.path.join(W, "src")):
    for fn in files:
        if not fn.endswith((".cu", ".cuh", ".cpp", ".hpp")):
            continue
        p = os.path.join(root, fn)
        s = io.open(p, encoding="utf-8").read()
        n = len(pat.findall(s))
        if n:
            s = pat.sub(r"mul_mat_q_case<\1, GGML_PREC_Q8>(", s)
            io.open(p, "w", encoding="utf-8", newline="").write(s)
            changed.append((fn, "case", n))

# 2) get_config fifth argument
pat2 = re.compile(r"ggml_cuda_mmq_get_config\(([^()]*(?:\([^()]*\))?[^()]*?)\)")
for root, _, files in os.walk(os.path.join(W, "src")):
    for fn in files:
        if not fn.endswith((".cu", ".cuh", ".cpp", ".hpp")):
            continue
        p = os.path.join(root, fn)
        s = io.open(p, encoding="utf-8").read()
        n = 0

        def sub(m):
            global n
            args = m.group(1)
            if "GGML_PREC" in args:
                return m.group(0)
            n += 1
            return "ggml_cuda_mmq_get_config(%s, GGML_PREC_Q8)" % args

        s2 = pat2.sub(sub, s)
        if s2 != s:
            io.open(p, "w", encoding="utf-8", newline="").write(s2)
            changed.append((fn, "get_config", n))

# 3) the narrowing in the mmq_args initialiser
p = os.path.join(W, "src/prefill/moe_mmq.cu")
s = io.open(p, encoding="utf-8").read()
old = "                        p.max_rows, p.max_rows};"
new = "                        (int) p.max_rows, (int) p.max_rows};"
if old in s:
    io.open(p, "w", encoding="utf-8", newline="").write(s.replace(old, new, 1))
    changed.append(("moe_mmq.cu", "narrowing", 1))

for c in changed:
    print("%-28s %-12s %d" % c)
print("files touched:", len(changed))
