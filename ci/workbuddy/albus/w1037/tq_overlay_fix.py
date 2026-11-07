import io, os, shutil

WT = "/home/albus/strata166/pr/k10"
P = os.path.join(WT, "cmake/strata_ggml_tq_overlay.cmake")
s = io.open(P, encoding="utf-8").read()

OLD = '''  if(NOT _sig_new LESS 0)
    set(_ps ", prec_src1")
    set(_pfb ", false")
    set(_pa ", GGML_PREC_Q8")'''
NEW = '''  if(NOT _sig_new LESS 0)
    set(_ps ", prec_src1")
    set(_pa ", GGML_PREC_Q8")
    # W1037: the write-back's 5th template argument (has_fusion / ", false") exists only where upstream still
    # passes it.  b12110 dropped it, so probe the write-back's own signature instead of inferring it from
    # get_nthreads -- inferring is what produced "no matching constructor for ggml_cuda_mmq_util_funcs" here.
    string(FIND "${_m}" "ggml_cuda_mmq_write_back_mma<type, J, fallback, prec_src1, " _wb5)
    if(NOT _wb5 LESS 0)
      set(_pfb ", false")
    endif()'''

if NEW in s:
    print("already patched")
elif OLD in s:
    shutil.copy2(P, P + ".bak_w1037")
    io.open(P, "w", encoding="utf-8", newline="\n").write(s.replace(OLD, NEW, 1))
    print("patched", P)
else:
    raise SystemExit("FAIL: anchor not found")
