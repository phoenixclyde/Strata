#!/usr/bin/env python3
"""Port the HIP MMQ call sites to llama.cpp b12129's signatures.

b11062 (3cf0325):  ggml_cuda_mmq_get_config(type, J, fallback, cc)
                   mul_mat_q_case<type>(ctx, args, stream)
b12129:            ggml_cuda_mmq_get_config(type, J, fallback, cc, prec_src1)
                   mul_mat_q_case<type, prec_src1>(ctx, args, stream)

Only the two files the HIP build actually compiles are touched; the CUDA-only tab
copies (moe_mmq_tab.cuh) already use the 5-argument form.
"""
import io, re, sys

FILES = ["/home/albus/strata166/pr/strata-fork/src/prefill/moe_mmq.cu",
         "/home/albus/strata166/pr/strata-fork/src/prefill/mmq_kq_lib.cu"]

total_cfg = total_case = 0
for p in FILES:
    s = io.open(p, encoding="utf-8").read()
    out = []
    for line in s.split("\n"):
        n0 = line
        if "ggml_cuda_mmq_get_config(" in line and "GGML_PREC_" not in line:
            # the call always ends with ", cc)" on these lines (cc may be an expression)
            line2 = re.sub(r",\s*([A-Za-z0-9_\.\[\]]+)\)\s*;", r", \1, GGML_PREC_Q8);", line)
            if line2 != line:
                total_cfg += 1
                line = line2
        if "mul_mat_q_case<GGML_TYPE_" in line and "GGML_PREC_" not in line:
            line2 = re.sub(r"mul_mat_q_case<(GGML_TYPE_[A-Z0-9_]+)>",
                           r"mul_mat_q_case<\1, GGML_PREC_Q8>", line)
            if line2 != line:
                total_case += 1
                line = line2
        out.append(line)
    s2 = "\n".join(out)
    if s2 != s:
        io.open(p, "w", encoding="utf-8", newline="\n").write(s2)
    print("%s: changed" % p.split("/")[-1])

print("get_config sites: %d, mul_mat_q_case sites: %d" % (total_cfg, total_case))
