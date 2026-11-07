# -*- coding: utf-8 -*-
"""Parse the ncols 1..8 x (R=1 | R=table) sweep into the project's IlRows-style table."""
import re
import io

rows = []          # (cols, rarm, shape, mb, us)
cols = rarm = None
for line in io.open(r"C:\Users\clyde\..\..\..\dev\null", "r") if False else io.open(
        r"D:\workbuddy_space\strata_ws\albus\w863\sweep_cols.txt", encoding="utf-8", errors="replace"):
    m = re.match(r"#### cols=(\d+) rows=(\d+) ####", line)
    if m:
        cols, rarm = int(m.group(1)), int(m.group(2))
        continue
    m = re.match(r"\s{2}(.+?)\s+(\d+)->(\d+)\s+([\d.]+) MB\s+([\d.]+) us", line)
    if m and cols is not None:
        rows.append((cols, rarm, m.group(1).strip(), int(m.group(2)), int(m.group(3)), float(m.group(4)), float(m.group(5))))

shapes = []
for r in rows:
    if r[2] not in shapes:
        shapes.append(r[2])

print("parsed %d measurements, %d shapes" % (len(rows), len(shapes)))

def get(c, arm, shape):
    for r in rows:
        if r[0] == c and r[1] == arm and r[2] == shape:
            return r[6], r[5]
    return None, None

print("\n=== per-shape: us at R=1 / R=table, speedup (real kernel, production flags) ===")
hdr = "%-24s %5s" % ("shape", "MB")
for c in range(1, 9):
    hdr += " %13s" % ("n=%d" % c)
print(hdr)
for s in shapes:
    mb = get(1, 1, s)[1]
    line = "%-24s %5.2f" % (s, mb)
    for c in range(1, 9):
        a, _ = get(c, 1, s)
        b, _ = get(c, 0, s)
        line += " %6.1f/%5.1f" % (a, b) if a and b else " %13s" % "-"
    print(line)

print("\n=== speedup table (R=table / R=1); '.' = within noise, 'x' = slower ===")
print("%-24s %5s" % ("shape", "MB") + "".join(" %7s" % ("n=%d" % c) for c in range(1, 9)))
for s in shapes:
    line = "%-24s %5.2f" % (s, get(1, 1, s)[1])
    for c in range(1, 9):
        a, _ = get(c, 1, s)
        b, _ = get(c, 0, s)
        if not a or not b:
            line += " %7s" % "-"
            continue
        sp = a / b
        line += " %7.3f" % sp
    print(line)

print("\n=== whole-layer sum (9 matrices, 106.54 MB) ===")
print("%-6s %12s %12s %10s" % ("ncols", "R=1 us", "R=table us", "speedup"))
for c in range(1, 9):
    a = sum(get(c, 1, s)[0] for s in shapes if get(c, 1, s)[0])
    b = sum(get(c, 0, s)[0] for s in shapes if get(c, 0, s)[0])
    print("%-6d %12.1f %12.1f %10.3f" % (c, a, b, a / b))

print("\n=== IlRows-style kept cells (win >= 3%, both arms present) ===")
for s in shapes:
    kept = []
    for c in range(1, 9):
        a, _ = get(c, 1, s)
        b, _ = get(c, 0, s)
        if a and b and a / b >= 1.03:
            kept.append("n%d:%.2fx" % (c, a / b))
    print("%-24s %s" % (s, ", ".join(kept) if kept else "(none)"))

# what the R table actually picks, from the patch's own rule
print("\n=== note: 'table' arm = wave_rows_for() rule (R*NCOLS<=12, n_out/(4R)>=120) ===")
