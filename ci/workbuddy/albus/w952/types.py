# -*- coding: utf-8 -*-
"""Determine which ggml type ids production actually instantiates, per path."""
import json, collections, os, sys

PACK = "/home/albus/strata166/data/packs/ud-q4_k_xl"
T = {0:"F32",1:"F16",2:"Q4_0",3:"Q4_1",6:"Q5_0",7:"Q5_1",8:"Q8_0",9:"Q8_1",10:"Q2_K",11:"Q3_K",
     12:"Q4_K",13:"Q5_K",14:"Q6_K",15:"Q8_K",16:"IQ2_XXS",17:"IQ2_XS",18:"IQ3_XXS",19:"IQ1_S",
     20:"IQ4_NL",21:"IQ3_S",22:"IQ2_S",23:"IQ4_XS",24:"I8",25:"I16",26:"I32",27:"I64",28:"F64",
     29:"IQ1_M",30:"BF16",31:"Q4_0_4_4",32:"Q4_0_4_8",33:"Q4_0_8_8",34:"TQ1_0",35:"TQ2_0",36:"IQ4_NL_4_4",
     37:"IQ4_NL_4_8",38:"IQ4_NL_8_8",39:"MXFP4"}

print("=== dense tensors (compat-bf16.json) ===")
d = json.load(open(os.path.join(PACK, "compat-bf16.json")))
t = d["tensors"]
c = collections.Counter(x["source_type"] for x in t)
b = collections.Counter()
for x in t:
    b[x["source_type"]] += x["bytes"]
tot = sum(b.values())
print("count:", len(t), "| by type:", dict(c))
print("bytes GB: %.2f | share:" % (tot / 1e9), {k: round(100.0 * v / tot, 1) for k, v in b.items()})
# names that are not hc_* (attention/head/etc)
other = collections.Counter()
for x in t:
    if ".hc_" not in x["name"]:
        other[(x["name"].split(".")[-2] if "." in x["name"] else x["name"], x["source_type"])] += x["bytes"]
print("non-hc tensors top:", [(k, round(v / 1e9, 2)) for k, v in sorted(other.items(), key=lambda kv: -kv[1])[:6]])

print()
print("=== experts (native_experts.txt) ===")
rows = []
for ln in open(os.path.join(PACK, "native_experts.txt")):
    if ln.startswith("#") or not ln.strip():
        continue
    f = ln.split()
    if len(f) < 5:
        continue
    rows.append((int(f[0]), int(f[1]), int(f[2]), int(f[3]), int(f[4])))
print("layers:", len(rows))
print("gu:", {T.get(k, k): v for k, v in collections.Counter(r[1] for r in rows).items()})
print("d :", {T.get(k, k): v for k, v in collections.Counter(r[2] for r in rows).items()})
gb = sum(r[3] for r in rows) / 1e9
print("expert blob GB: %.2f | share:" % gb,
      {T.get(k, k): v for k, v in collections.Counter(
          {12: 0}).items()})
sh = collections.Counter()
for r in rows:
    sh[T.get(r[1], r[1]) + "/" + T.get(r[2], r[2])] += r[3]
print("pairs:", {k: round(100.0 * v / sum(sh.values()), 1) for k, v in sh.most_common()})
