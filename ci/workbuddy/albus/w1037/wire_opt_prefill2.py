import io, shutil, sys

P = "/home/albus/strata166/pr/port-all/src/kernels/cuda/qsa_decode_attn.cu"
s = io.open(P, encoding="utf-8").read()
if "opt_chunk" in s:
    print("already patched")
    sys.exit(0)

ANCHOR = "    if (lane_cell) {\n        if (kv_mode == 3) STRATA_ATTN_LC(3);"
NEW = """#if defined(STRATA_HIP_GFX906)
    // W1037: the gfx906 OPT switches (DPP / DP4A / LDS pad) were wired into qsa_decode_attn_batch_rows and
    // qsa_decode_attn_slots only.  Prefill attention calls qsa_decode_attn_batch -> launch_chunks_batch ->
    // attn_chunk_kernel<M> (the plain instantiation), so on the production path they were dead code: with all
    // four switches on, the measured `qsa attn` phase did not move (578.3 -> 577.3 ms at 2.5K).
    if (const int opt_chunk = gfx906_attn_opt();
        opt_chunk != 0 && !lane_cell && !use_query_swizzle && (kv_mode == 3 || kv_mode == 1)) {
        if (kv_mode == 3) STRATA_ATTN_OPT_DISPATCH(STRATA_ATTN_OPT_BATCH, 3)
        else STRATA_ATTN_OPT_DISPATCH(STRATA_ATTN_OPT_BATCH, 1)
        return;   // the caller runs the merge pass
    }
#endif
    if (lane_cell) {
        if (kv_mode == 3) STRATA_ATTN_LC(3);"""

n = s.count(ANCHOR)
print("anchor count:", n)
if n != 1:
    print("FAIL: anchor not unique")
    sys.exit(2)
shutil.copy2(P, P + ".bak_w1037g")
s = s.replace(ANCHOR, NEW, 1)
io.open(P, "w", encoding="utf-8", newline="\n").write(s)
print("patched")
