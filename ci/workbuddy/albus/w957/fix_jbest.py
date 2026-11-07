# -*- coding: utf-8 -*-
"""R90-S3 fix: 0.8.0 replaced mmq_args' `ncols_opt` with `int J_best` and aborts unless it is a valid tile width.
Our positional initialiser put max_rows (412) there -> GGML_ABORT at mmq.cuh:1594.
Add the same "fewest tiles that fit" choice upstream makes (its helper is static in mmq.cu) and use it.
"""
import io, sys

W = sys.argv[1]
p = W + "/src/prefill/moe_mmq.cu"
s = io.open(p, encoding="utf-8").read()

HELPER = '''
// 0.8.0 (b12099) replaced mmq_args' `int64_t ncols_opt` with `int J_best` and dispatches on it
// (mul_mat_q_switch_J aborts on anything outside 8..128).  Upstream's ggml_cuda_mmq_get_J_best is static in
// mmq.cu, so the same rule -- the tile width with the fewest tiles that fits the shared memory -- is repeated
// here.  Keep it next to fits(), which walks the same J ladder for the supported() test.
int pick_J(int t, int64_t ncols, bool fallback) {
    const ggml_cuda_device_info& info = ggml_cuda_info();
    int id = ggml_cuda_get_device();
    if (id < 0 || id >= info.device_count) id = 0;
    const int cc = info.devices[id].cc;
    const size_t smpbo = info.devices[id].smpbo;
    int best = 0, ntiles_best = INT_MAX;
    for (int J = 8; J <= 128 && ntiles_best > 1; J += 8) {
        const ggml_cuda_mmq_config c = ggml_cuda_mmq_get_config((ggml_type) t, J, fallback, cc, GGML_PREC_Q8);
        if (c.type == GGML_TYPE_COUNT) continue;
        if (mmq_get_nbytes_shared(c, cc) > smpbo) continue;
        const int ntiles = (int) ((ncols + c.J - 1) / c.J);
        if (ntiles < ntiles_best) { best = J; ntiles_best = ntiles; }
    }
    return best > 0 ? best : 64;
}

size_t matrix_bytes(int t, int64_t rows, int64_t cols) {'''

anchor_a = "size_t matrix_bytes(int t, int64_t rows, int64_t cols) {"
anchor_b = "    const mmq_args a = {(const char*) p.w, t, (const int*) p.xq, p.ids, p.bounds, p.dst, p.y_scale,"
anchor_c = "                        (int) p.max_rows, (int) p.max_rows};"

ok = []
if "int pick_J(" not in s and anchor_a in s:
    s = s.replace(anchor_a, HELPER.lstrip("\n"), 1)
    ok.append("helper")
if "const int J_best = pick_J(" not in s and anchor_b in s:
    s = s.replace(anchor_b,
                  "    // 0.8.0: J_best selects the instantiation; the fallback flag follows upstream's rows%128 rule.\n"
                  "    const bool mmq_fb = p.w_rows % 128 != 0;\n"
                  "    const int  J_best = pick_J((int) t, p.max_rows, mmq_fb);\n" + anchor_b, 1)
    ok.append("compute")
if anchor_c in s:
    s = s.replace(anchor_c, "                        (int) p.max_rows, (int) J_best};", 1)
    ok.append("init")
io.open(p, "w", encoding="utf-8", newline="").write(s)
print("patched:", ok)
