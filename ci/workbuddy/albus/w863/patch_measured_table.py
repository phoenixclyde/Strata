#!/usr/bin/env python3
"""W863: replace W862's wave-rows formula with the MEASURED table.

Backs the file up to native_mmvq.cu.w863bak (the formula state) and is idempotent.
Rollback: cp native_mmvq.cu.w863bak native_mmvq.cu   (back to the W862 formula)
          cp native_mmvq.cu.w862bak native_mmvq.cu   (back to HEAD, no wave rows at all)
"""
import os
import shutil
import sys

SRC = "/home/albus/strata166/pr/strata-fork/src/kernels/cuda/native_mmvq.cu"
BAK = SRC + ".w863bak"

OLD = """int wave_rows_for(int ncols, int n_in, int n_out) {
    if (g_wave_rows > 0) return g_wave_rows;
    int R = 2;
    if (ncols <= 2 && n_in / 32 >= 32 && n_out >= 2048) R = 4;
    while (R > 1 && n_out / (4 * R) < 120) R >>= 1;
    return R;
}"""

NEW = """// W863: MEASURED table (real kernel, production flags, gfx906, 2026-11-01).  It replaces the
// W862 formula, which picked R = 4 at ncols = 1 and cost 0.982x there (out 6144->2560: 28.4 ->
// 31.3 us).  Cell = the fastest of R in {1,2,4} that beat R = 1 by >= 3 % on that shape at that
// column count; ncols = 1 stays at R = 1 (the differences there were not reproducible across
// arms).  0 means R = 1.  An unmeasured shape keeps the old behaviour: R = 1.
//   tool: albus/w862/q8_group_bench.cpp --group single --cols N --rows {1,2,4}
static const struct { int n_in, n_out; unsigned char r[8]; } kWaveRows[] = {
    {  2560, 10240, {0, 4, 4, 4, 2, 2, 2, 2}},   // GDN qkv
    {  2560,  6144, {0, 2, 2, 2, 2, 2, 2, 2}},   // GDN gate
    {  6144,  2560, {0, 2, 4, 4, 2, 2, 2, 2}},   // GDN/QSA out
    {  2560, 12288, {0, 2, 2, 2, 2, 2, 2, 2}},   // QSA q
    {  2560,   512, {0, 0, 2, 2, 2, 2, 2, 2}},   // QSA k/v
    { 10240,   320, {0, 0, 2, 2, 2, 2, 2, 2}},   // HC down
    {   320, 10240, {0, 2, 2, 2, 2, 0, 2, 0}},   // HC up
    {  2560,   640, {0, 0, 2, 2, 2, 2, 2, 2}},   // shared g/u
    {   640,  2560, {0, 0, 2, 2, 2, 2, 2, 2}},   // shared down
};

int wave_rows_for(int ncols, int n_in, int n_out) {
    if (g_wave_rows > 0) return g_wave_rows;   // STRATA_MMVQ_WAVE_ROWS / native_mmvq_set_wave_rows
    if (ncols < 1 || ncols > 8) return 1;
    for (const auto& e : kWaveRows)
        if (e.n_in == n_in && e.n_out == n_out) {
            const int R = e.r[ncols - 1];
            return R == 0 ? 1 : R;
        }
    return 1;   // an unmeasured shape keeps the old behaviour
}"""

s = open(SRC, encoding="utf-8").read()
if "kWaveRows" in s:
    print("already patched (kWaveRows present)")
    sys.exit(0)
if not os.path.exists(BAK):
    shutil.copy2(SRC, BAK)
    print("backup ->", BAK)
assert OLD in s, "W862 formula body not found"
s = s.replace(OLD, NEW, 1)
open(SRC, "w", encoding="utf-8", newline="\n").write(s)
print("patched", SRC, len(s), "bytes")
