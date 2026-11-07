import io, shutil, sys

P = "/home/albus/strata166/pr/port-all/src/kernels/cuda/qsa_decode_attn.cu"
s = io.open(P, encoding="utf-8").read()

ANCHOR = "#endif\n    if (kv_mode == 3)\n        STRATA_ATTN_CHUNK_SEL(3, pre)"
NEW = """#endif
#if defined(STRATA_HIP_GFX906)
    // W1037: the gfx906 OPT switches (DPP / DP4A / LDS pad) were wired into qsa_decode_attn_batch_rows and
    // qsa_decode_attn_slots only.  Prefill attention calls qsa_decode_attn_batch -> launch_chunks_batch -> the
    // plain attn_chunk_kernel<M>, so on the production path they were dead code (measured: the qsa attn phase
    // did not move by a single ms with all four switches on).  Select the OPT instantiation here as well.
    else if (const int opt_chunk = gfx906_attn_opt(); opt_chunk != 0 && (kv_mode == 3 || kv_mode == 1)) {
        if (kv_mode == 3) STRATA_ATTN_OPT_DISPATCH(STRATA_ATTN_OPT_BATCH, 3)
        else STRATA_ATTN_OPT_DISPATCH(STRATA_ATTN_OPT_BATCH, 1)
    }
#endif
    else if (kv_mode == 3)
        STRATA_ATTN_CHUNK_SEL(3, pre)"""

n = s.count(ANCHOR)
print("anchor count:", n)
if n != 1:
    print("FAIL: anchor not unique")
    sys.exit(2)

shutil.copy2(P, P + ".bak_w1037f")
s = s.replace(ANCHOR, NEW, 1)
io.open(P, "w", encoding="utf-8", newline="\n").write(s)
print("patched:", P)
