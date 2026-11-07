#!/usr/bin/env python3
"""W1031 / R100: adapt Strata's three MMQ glue TUs to llama.cpp 0.9.0 (b12110) headers.

Only the API surface changed upstream:
  * ggml_cuda_mmq_get_config(type, J, fallback, cc)                  -> (..., cc, prec_src1)
  * mul_mat_q_case<T>(...)                                          -> mul_mat_q_case<T, prec_src1>(...)
  * ggml_backend_cuda_context::new_pool_for_device(int,int)  (member) -> static (ctx&, int, int)
Both call sites in our glue always feed a pre-quantised Q8_1 activation, so prec_src1 = GGML_PREC_Q8
(mmq.cu in 0.9.0 does the same for every non-FP4 type).
"""
import re, sys, pathlib

ROOT = pathlib.Path("/home/albus/strata166/w1031/src-v090/src/prefill")

def patch(path, subs):
    p = ROOT / path
    s = p.read_text()
    orig = s
    for pat, rep, cnt in subs:
        s, n = re.subn(pat, rep, s, flags=re.M)
        print(f"{path}: {pat[:52]!r} -> {n} hit(s) (expected {cnt})")
        if n != cnt:
            print("  !! unexpected count", file=sys.stderr)
    if s != orig:
        p.write_text(s)
        print(f"{path}: written")
    else:
        print(f"{path}: UNCHANGED")

# 1) get_config gains prec_src1 (every call in our glue is Q8_1)
patch("moe_mmq.cu", [
    (r'(ggml_cuda_mmq_get_config\([^;\n]*?), (cc|info\.devices\[id\]\.cc)\)', r'\1, \2, GGML_PREC_Q8)', 5),
    (r'(mul_mat_q_case<GGML_TYPE_[A-Z0-9_]+)>', r'\1, GGML_PREC_Q8>', 20),
])

# 2) the NVFP4 W4A8 wrapper instantiates the renamed case template
patch("mmq_nvfp4_w4a8.cu", [
    (r'(strata_w4a8_mul_mat_q_case<GGML_TYPE_NVFP4)>', r'\1, GGML_PREC_Q8>', 2),
])

# 3) the pool factory became static and takes the context
patch("ggml_cuda_host.cu", [
    (r'std::unique_ptr<ggml_cuda_pool> ggml_backend_cuda_context::new_pool_for_device\(int, int\) \{',
     'std::unique_ptr<ggml_cuda_pool> ggml_backend_cuda_context::new_pool_for_device(ggml_backend_cuda_context &, int, int) {', 1),
])
print("done")
