#!/usr/bin/env python3
"""W948: how far is each gfx906 fork's mmq.cuh from the scheduler we mirrored?
CMake gates STRATA_MMQ_TAB on the sha256 of the region [mul_mat_q_process_tile .. #define DECL_MMQ_CASE)."""
import hashlib, os, subprocess, sys

KNOWN = "36e4dc716c504470ec09cc0852d29a6ac5eace257f6e5e72db3805ca4f043eb0"
A = "static __device__ __forceinline__ void mul_mat_q_process_tile"
B = "#define DECL_MMQ_CASE"

files = ["/home/albus/strata166/llama.cpp/ggml/src/ggml-cuda/mmq.cuh"] + [
    "/home/albus/strata166/ref/llama_variants/mmq_%s.cuh" % n for n in ("furnace", "exabit", "mx")]

def region(path):
    s = open(path, encoding="utf-8", errors="replace").read().replace("\r\n", "\n")
    i = s.find(A)
    j = s.find(B, i) if i >= 0 else -1
    if i < 0 or j < 0:
        return None, s
    return s[i:j], s

print("pin (ours) mirror-region sha256:", KNOWN)
for p in files:
    r, whole = region(p)
    h = hashlib.sha256(r.encode()).hexdigest() if r else "REGION-NOT-FOUND"
    name = os.path.basename(p)
    mark = "  <== same region as our mirror" if h == KNOWN else ""
    print("%-22s %7d B  lines=%5d  region=%s%s" % (name, len(whole.encode()), whole.count("\n"), h[:16] + "...", mark))

# line-level diff against ours
base = files[0]
for p in files[1:]:
    d = subprocess.run(["diff", "-u", base, p], capture_output=True, text=True).stdout
    add = sum(1 for l in d.split("\n") if l.startswith("+") and not l.startswith("+++"))
    rem = sum(1 for l in d.split("\n") if l.startswith("-") and not l.startswith("---"))
    print("%-22s diff vs ours: +%d / -%d lines" % (os.path.basename(p), add, rem))
