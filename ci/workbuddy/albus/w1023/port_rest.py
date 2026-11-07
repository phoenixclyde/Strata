#!/usr/bin/env python3
"""Finish the b12129 port: the pool override signature and the two NVFP4 wrappers.

b11062 declared  new_pool_for_device(int, int);  b12129 is back to (context &, int, int).
b11062's mul_mat_q_case had one template parameter; b12129 has <type, prec>, and the
W4A4 variant is expressed with GGML_PREC_Q4 (the macro DECL_MMQ_CASE_W4A4 exists for it).
"""
import io

R = "/home/albus/strata166/pr/strata-fork/src/prefill/"
def edit(name, pairs):
    p = R + name
    s = io.open(p, encoding="utf-8").read()
    for a, b in pairs:
        assert a in s, (name, a[:60])
        s = s.replace(a, b, 1)
    io.open(p, "w", encoding="utf-8", newline="\n").write(s)
    print("patched", name)

edit("ggml_cuda_host.cu", [
    ("ggml_backend_cuda_context::new_pool_for_device(int, int) {",
     "ggml_backend_cuda_context::new_pool_for_device(ggml_backend_cuda_context &, int, int) {"),
])
edit("mmq_nvfp4_w4a8.cu", [
    ("strata_w4a8_mul_mat_q_case<GGML_TYPE_NVFP4>(ctx, a, s);",
     "strata_w4a8_mul_mat_q_case<GGML_TYPE_NVFP4, GGML_PREC_Q8>(ctx, a, s);"),
])
edit("mmq_nvfp4_w4a4.cu", [
    ("DECL_MMQ_CASE(GGML_TYPE_NVFP4);", "DECL_MMQ_CASE_W4A4(GGML_TYPE_NVFP4);"),
    ("strata_w4a4_mul_mat_q_case<GGML_TYPE_NVFP4>(ctx, a, s);",
     "strata_w4a4_mul_mat_q_case<GGML_TYPE_NVFP4, GGML_PREC_Q4>(ctx, a, s);"),
])
print("ok")
