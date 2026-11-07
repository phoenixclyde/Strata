# -*- coding: utf-8 -*-
"""Emit the measured wave-rows table as a C++ snippet + the doc's table."""
import io
import re

rows = {}
shapes = []
DIM = {}


def load(path):
    cols = rarm = None
    for line in io.open(path, encoding="utf-8", errors="replace"):
        m = re.match(r"#### cols=(\d+) rows=(\d+) ####", line)
        if m:
            cols, rarm = int(m.group(1)), int(m.group(2))
            continue
        m = re.match(r"\s{2}(.+?)\s+(\d+)->(\d+)\s+([\d.]+) MB\s+([\d.]+) us", line)
        if m and cols is not None:
            k = (cols, rarm, m.group(1).strip())
            rows[k] = (float(m.group(4)), float(m.group(5)))
            if m.group(1).strip() not in shapes:
                shapes.append(m.group(1).strip())
            DIM[m.group(1).strip()] = (int(m.group(2)), int(m.group(3)))


load(r"D:\workbuddy_space\strata_ws\albus\w863\sweep_cols.txt")
load(r"D:\workbuddy_space\strata_ws\albus\w863\sweep_r24.txt")

# ncols=1: the arms disagree by <3 % everywhere except HC up (a 3.5 MB matrix, 320->10240).
# Force R=1 there (production's current behaviour) instead of taking a noise win.
FORCE_R1_AT_N1 = True

pick = {}
for s in shapes:
    for c in range(1, 9):
        arms = {r: rows[(c, r, s)][1] for r in (1, 2, 4) if (c, r, s) in rows}
        if 1 not in arms:
            continue
        best = min(arms, key=lambda k: arms[k])
        gain = arms[1] / arms[best]
        p = best if gain >= 1.03 else 1
        if FORCE_R1_AT_N1 and c == 1:
            p = 1
        pick[(s, c)] = p

# stable shape order: the bench's own order
order = ["GDN qkv", "GDN gate", "GDN/QSA out", "QSA q", "QSA k/v",
         "HC down", "HC up", "shared g/u", "shared down"]
order = [s for s in order if s in shapes]

out = io.StringIO()
out.write("// W863: MEASURED rows-per-wavefront table (real kernel, production flags, gfx906).\n")
out.write("// Replaces W862's formula. 0 = R=1 (the old one-row-per-wavefront behaviour).\n")
out.write("// Cell = fastest of R in {1,2,4}, kept only when it beat R=1 by >= 3 % on that shape\n")
out.write("// at that column count; ncols=1 is forced to R=1 (the 3 %-level differences there were\n")
out.write("// not reproducible across arms). Measured 2026-11-01, 40 iters/cell, tool:\n")
out.write("// albus/w862/q8_group_bench.cpp --group single --cols N --rows {1,2,4}\n")
out.write("static const struct { int n_in, n_out; const unsigned char r[8]; } kWaveRows[] = {\n")
for s in order:
    nin, nout = DIM[s]
    vals = ", ".join(str(pick[(s, c)]) if pick[(s, c)] != 1 else "0" for c in range(1, 9))
    out.write("    {%5d, %5d, {%s}},   // %s\n" % (nin, nout, vals, s))
out.write("};\n")
out.write("""
int wave_rows_for(int ncols, int n_in, int n_out) {
    if (g_wave_rows > 0) return g_wave_rows;          // STRATA_MMVQ_WAVE_ROWS / setter
    if (ncols < 1 || ncols > 8) return 1;
    for (const auto& e : kWaveRows)
        if (e.n_in == n_in && e.n_out == n_out) {
            const int R = e.r[ncols - 1];
            return R == 0 ? 1 : R;
        }
    return 1;        // an unmeasured shape keeps the old behaviour
}
""")
io.open(r"D:\workbuddy_space\strata_ws\albus\w863\measured_table.cpp.txt", "w", encoding="utf-8", newline="\n").write(out.getvalue())
print(out.getvalue())

# doc table: gain at each column count vs R=1, formula vs measured
print("\n| ncols | R=1 µs | 公式(现在树里) | 实测表 |")
def formula(nc, nin, nout):
    R = 2
    if nc <= 2 and nin // 32 >= 32 and nout >= 2048:
        R = 4
    while R > 1 and nout // (4 * R) < 120:
        R >>= 1
    return R
for c in range(1, 9):
    t1 = tf = tm = 0.0
    for s in shapes:
        if (c, 1, s) not in rows:
            continue
        t1 += rows[(c, 1, s)][1]
        nin, nout = DIM[s]
        f = formula(c, nin, nout)
        tf += rows.get((c, f, s), rows[(c, 1, s)])[1]
        p = pick[(s, c)]
        tm += rows.get((c, p, s), rows[(c, 1, s)])[1]
    print("| %d | %.1f | %.1f (%.3f×) | %.1f (%.3f×) |" % (c, t1, tf, t1 / tf, tm, t1 / tm))
