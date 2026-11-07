#!/usr/bin/env python3
"""W1040: per-symbol instruction mix of the attn kernels (OPT=0 vs OPT=2) from the built object."""
import re
import subprocess

OBJ = "/tmp/qda.o"
DUMP = "/tmp/qda.dis"

# rebuild the object exactly as ninja does (so the ISA is the one that shipped)
cmd = subprocess.run(["bash", "-lc",
                      'cd /out && ninja -t commands CMakeFiles/strata_kernels.dir/src/kernels/cuda/qsa_decode_attn.cu.o | tail -1'],
                     capture_output=True, text=True)
line = cmd.stdout.strip()
line = line.replace("-o CMakeFiles/strata_kernels.dir/src/kernels/cuda/qsa_decode_attn.cu.o", "-o " + OBJ)
r = subprocess.run(["bash", "-lc", line], capture_output=True, text=True, cwd="/out")
print("compile rc", r.returncode, r.stderr[-300:])

d = subprocess.run(["/opt/rocm/lib/llvm/bin/llvm-objdump", "-d", "--mcpu=gfx906", OBJ],
                   capture_output=True, text=True)
print("objdump lines", d.stdout.count("\n"), "err", d.stderr[-200:])

cur = None
hist = {}
for ln in d.stdout.split("\n"):
    m = re.match(r"^[0-9a-f]+ <(.+)>:$", ln)
    if m:
        cur = m.group(1)
        hist.setdefault(cur, {})
        continue
    m2 = re.search(r"\s([a-z][a-z0-9_]+)\s", ln)
    if cur and m2:
        op = m2.group(1)
        h = hist[cur]
        h[op] = h.get(op, 0) + 1

def short(n):
    return n[:120]

for name, h in hist.items():
    if "attn_chunk_kernel" not in name:
        continue
    total = sum(h.values())
    print("\n%s\ntotal=%d  dot4=%d  fma=%d  cvt=%d  rcp=%d  max=%d  shfl/bperm=%d  lds_w=%d" % (
        short(name), total, h.get("v_dot4_i32_i8", 0), h.get("v_fma_f32", 0),
        h.get("v_cvt_f32_i32", 0), h.get("v_rcp_iflag_f32", 0) + h.get("v_rcp_f32", 0),
        h.get("v_max_f32", 0), h.get("ds_bpermute_b32", 0) + h.get("v_mov_b32_dpp", 0),
        h.get("ds_write_b32", 0) + h.get("ds_write_b64", 0) + h.get("ds_write2_b32", 0)))
