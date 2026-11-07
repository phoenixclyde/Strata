# -*- coding: utf-8 -*-
import collections
P = "/home/albus/strata166/data/packs/ud-q4_k_xl/native_experts.txt"
T = {0: "F32", 1: "F16", 2: "Q4_0", 3: "Q4_1", 6: "Q5_0", 7: "Q5_1", 8: "Q8_0",
     10: "Q2_K", 11: "Q3_K", 12: "Q4_K", 13: "Q5_K", 14: "Q6_K", 15: "Q8_K"}
rows = []
for ln in open(P):
    if ln.startswith("#") or not ln.strip():
        continue
    f = ln.split()
    if len(f) < 5:
        continue
    rows.append((int(f[0]), int(f[1]), int(f[2]), int(f[3]), int(f[4])))

print("layers:", len(rows))
print("gu_types:", dict(collections.Counter(T.get(r[1], r[1]) for r in rows)))
print("d_types :", dict(collections.Counter(T.get(r[2], r[2]) for r in rows)))
print("blob GB : %.1f" % (sum(r[3] for r in rows) / 1e9))
print("pairs:")
for (a, b), c in collections.Counter((r[1], r[2]) for r in rows).most_common():
    print("  gu=%-5s d=%-5s  layers=%d  bytes=%.2f GB" % (
        T.get(a, a), T.get(b, b), c, sum(r[3] for r in rows if r[1] == a and r[2] == b) / 1e9))
