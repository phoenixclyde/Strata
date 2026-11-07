# -*- coding: utf-8 -*-
"""Merge the three arms (R=1,2,4) into the project's IlRows-style measured table."""
import io
import re

rows = {}
shapes = []


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


load(r"D:\workbuddy_space\strata_ws\albus\w863\sweep_cols.txt")   # rows=1 and rows=0(formula)
load(r"D:\workbuddy_space\strata_ws\albus\w863\sweep_r24.txt")     # rows=2, rows=4

print("measurements: %d" % len(rows))

# the formula's own choice, so the table can be compared with what is in the tree
def formula(ncols, nin, nout):
    R = 2
    if ncols <= 2 and nin // 32 >= 32 and nout >= 2048:
        R = 4
    while R > 1 and nout // (4 * R) < 120:
        R >>= 1
    return R


SHAPE_DIM = {}
for (c, r, s), (mb, us) in rows.items():
    pass
# recover dims from the sweep text
DIM = {}
for path in (r"D:\workbuddy_space\strata_ws\albus\w863\sweep_cols.txt",):
    for line in io.open(path, encoding="utf-8", errors="replace"):
        m = re.match(r"\s{2}(.+?)\s+(\d+)->(\d+)\s", line)
        if m:
            DIM[m.group(1).strip()] = (int(m.group(2)), int(m.group(3)))

print("\n=== best R per (shape, ncols); us.  'best' = fastest arm, '-3%' rule vs R=1 ===")
print("%-22s %5s %s" % ("shape", "ncols", "  R=1      R=2      R=4   -> pick  gain"))
PICK = {}
for s in shapes:
    for c in range(1, 9):
        arms = {}
        for r in (1, 2, 4):
            v = rows.get((c, r, s))
            if v:
                arms[r] = v[1]
        if 1 not in arms:
            continue
        best = min(arms, key=lambda k: arms[k])
        gain = arms[1] / arms[best]
        pick = best if gain >= 1.03 else 1
        PICK[(s, c)] = (pick, arms[1] / arms[pick])
        print("%-22s %5d %7.1f  %7s  %7s  -> R=%d  %.3f" % (
            s, c, arms[1],
            ("%.1f" % arms[2]) if 2 in arms else "-",
            ("%.1f" % arms[4]) if 4 in arms else "-", pick, arms[1] / arms[pick]))

print("\n=== formula vs measured pick, per (shape,ncols) ===")
note = 0
for s in shapes:
    nin, nout = DIM.get(s, (0, 0))
    for c in range(1, 9):
        if (s, c) not in PICK:
            continue
        f = formula(c, nin, nout)
        p, g = PICK[(s, c)]
        if f != p:
            arms = {r: rows[(c, r, s)][1] for r in (1, 2, 4) if (c, r, s) in rows}
            tf = arms.get(f, arms.get(1))
            print("  %-22s n%d  formula R=%d (%.1f us) vs measured R=%d (%.1f us)  -> formula %.2f%% %s"
                  % (s, c, f, tf, p, arms[p], (tf / arms[p] - 1) * 100, "slower" if tf > arms[p] else "faster"))
            note += 1
print("  %d cells differ" % note)

print("\n=== whole-layer totals: formula (today) vs measured table vs R=1 ===")
tot = {1: 0.0, "f": 0.0, "m": 0.0}
for c in range(1, 9):
    t1 = tf = tm = 0.0
    for s in shapes:
        if (c, 1, s) not in rows:
            continue
        t1 += rows[(c, 1, s)][1]
        nin, nout = DIM.get(s, (0, 0))
        f = formula(c, nin, nout)
        tf += rows.get((c, f, s), rows[(c, 1, s)])[1]
        p, g = PICK[(s, c)]
        tm += rows.get((c, p, s), rows[(c, 1, s)])[1]
    print("ncols=%d  R=1 %7.1f us | formula %7.1f (%.3fx) | measured %7.1f (%.3fx)"
          % (c, t1, tf, t1 / tf, tm, t1 / tm))

print("\n=== production reality ===")
print("phase table: GDN qkv/q-idx gemv 2.44 ms/window over 36 layers = 67.8 us/layer")
print("bench qkv: n1 %.1f  n2 %.1f  n6 %.1f us" % (rows[(1, 1, "GDN qkv")][1], rows[(2, 1, "GDN qkv")][1],
                                                    rows[(6, 1, "GDN qkv")][1]))
