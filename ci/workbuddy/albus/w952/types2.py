# -*- coding: utf-8 -*-
"""Audit: expert byte share by blob_bytes (not offset) + dense.bin type histogram from index.txt."""
import collections, os

PACK = "/home/albus/strata166/data/packs/ud-q4_k_xl"
T = {0:"F32",1:"F16",2:"Q4_0",3:"Q4_1",6:"Q5_0",7:"Q5_1",8:"Q8_0",9:"Q8_1",10:"Q2_K",11:"Q3_K",
     12:"Q4_K",13:"Q5_K",14:"Q6_K",15:"Q8_K",16:"IQ2_XXS",17:"IQ2_XS",18:"IQ3_XXS",19:"IQ1_S",
     20:"IQ4_NL",21:"IQ3_S",22:"IQ2_S",23:"IQ4_XS",24:"I8",25:"I16",26:"I32",27:"I64",28:"F64",
     29:"IQ1_M",30:"BF16",34:"TQ1_0",35:"TQ2_0",39:"MXFP4"}

print("=== experts: correct byte column (blob_bytes = f[4]) ===")
rows = []
for ln in open(os.path.join(PACK, "native_experts.txt")):
    if ln.startswith("#") or not ln.strip():
        continue
    f = ln.split()
    if len(f) < 9:
        continue
    rows.append(dict(layer=int(f[0]), gu=int(f[1]), d=int(f[2]), off=int(f[3]), blob=int(f[4])))
tot = sum(r["blob"] for r in rows)
print("layers %d | blob total %.2f GiB" % (len(rows), tot / 2**30))
gu = collections.Counter(); 
for r in rows: gu[r["gu"]] += r["blob"]
print("gu by blob:", {T.get(k, k): "%.1f%%" % (100.0 * v / tot) for k, v in gu.items()})
pair = collections.Counter()
for r in rows: pair[(r["gu"], r["d"])] += r["blob"]
print("pairs by blob:", {"%s/%s" % (T.get(k[0]), T.get(k[1])): "%.1f%%" % (100.0 * v / tot) for k, v in pair.most_common()})
# offset-weighted (what W944 did)
toff = sum(r["off"] for r in rows)
po = collections.Counter()
for r in rows: po[(r["gu"], r["d"])] += r["off"]
print("pairs by OFFSET (W944 method):",
      {"%s/%s" % (T.get(k[0]), T.get(k[1])): "%.1f%%" % (100.0 * v / toff) for k, v in po.most_common()})

print()
print("=== dense.bin types from index.txt ===")
lines = [l.rstrip("\n") for l in open(os.path.join(PACK, "index.txt")) if not l.startswith("#")]
hdr = None
print("n lines", len(lines))
for l in lines[:2]:
    print(" sample:", l[:150])
# find type column: count fields
nf = collections.Counter(len(l.split()) for l in lines)
print("field counts:", nf)
