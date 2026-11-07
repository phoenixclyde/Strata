#!/usr/bin/env python3
"""W863: make STRATA_MMVQ_WAVE_ROWS real.

W862's docs (and the handover) promise "env STRATA_MMVQ_WAVE_ROWS=1 restores the old
behaviour, no rebuild" -- but nothing in the tree ever reads that variable: it appeared
only inside a comment.  Without it there is no runtime rollback and no in-image A/B.
This adds the read (once per process, static) in front of the measured table.
"""
import os
import shutil

SRC = "/home/albus/strata166/pr/strata-fork/src/kernels/cuda/native_mmvq.cu"
BAK = SRC + ".w863bak2"

OLD = """int wave_rows_for(int ncols, int n_in, int n_out) {
    if (g_wave_rows > 0) return g_wave_rows;   // STRATA_MMVQ_WAVE_ROWS / native_mmvq_set_wave_rows
    if (ncols < 1 || ncols > 8) return 1;"""

NEW = """// STRATA_MMVQ_WAVE_ROWS: 0/unset = the measured table, 1 = the old one-row-per-wavefront
// behaviour, 2 or 4 = that many rows for every call.  Read once per process.
static int wave_rows_env() {
    static const int v = [] {
        const char* s = std::getenv("STRATA_MMVQ_WAVE_ROWS");
        return s == nullptr ? 0 : std::atoi(s);
    }();
    return v < 0 ? 0 : v;
}

int wave_rows_for(int ncols, int n_in, int n_out) {
    if (g_wave_rows > 0) return g_wave_rows;   // native_mmvq_set_wave_rows (the bench)
    const int env = wave_rows_env();
    if (env > 0) return env;                   // STRATA_MMVQ_WAVE_ROWS, no rebuild
    if (ncols < 1 || ncols > 8) return 1;"""

s = open(SRC, encoding="utf-8").read()
if "wave_rows_env" in s:
    print("already patched (wave_rows_env present)")
    raise SystemExit(0)
if "kWaveRows" not in s:
    raise SystemExit("apply patch_measured_table.py first")
if not os.path.exists(BAK):
    shutil.copy2(SRC, BAK)
    print("backup ->", BAK)
assert OLD in s, "table body anchor not found"
s = s.replace(OLD, NEW, 1)
open(SRC, "w", encoding="utf-8", newline="\n").write(s)
print("patched", SRC, len(s), "bytes")
