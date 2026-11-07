#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""W1042: zero-downtime ISA probe.  Same attn TU, one variable: intrinsics.hpp.

  base -> k10@af797b90 (production, no gfx906 dot4 branch)
  a0   -> port-all@79516b21 (A0: __builtin_amdgcn_sdot4 on gfx906)

Run INSIDE the build container with /out = build-masterp and /w = tmp/w1042.
It never touches the source tree and never launches a kernel.
"""
import io
import re
import shlex
import subprocess
import sys

T = "CMakeFiles/strata_kernels.dir/src/kernels/cuda/qsa_decode_attn.cu.o"
OPS = ["v_dot4_i32_i8", "v_dot8_i32_i4", "v_mad_i32_i24", "v_mul_i32_i24",
       "v_cndmask_b32", "v_or_b32", "v_perm_b32", "v_add3_u32", "v_fma_f32",
       "v_fmac_f32", "ds_bpermute_b32"]


def build_cmd():
    lines = subprocess.check_output(["ninja", "-t", "commands", T], text=True).strip().splitlines()
    cand = [l for l in lines if "qsa_decode_attn.cu" in l and " -c " in " " + l]
    if not cand:
        print("NO COMPILE COMMAND; lines=" + str(len(lines)))
        sys.exit(2)
    a = shlex.split(cand[-1])
    out, skip = [], False
    for x in a:
        if skip:
            skip = False
            continue
        if x == "-c":
            continue
        if x == "-o":
            skip = True
            continue
        out.append(x)
    return out


def main():
    base = build_cmd()
    print("compiler:", base[0])
    print("has --offload-arch=gfx906:", any("gfx906" in x for x in base))
    print("has -DSTRATA_HIP_GFX906=1:", any("STRATA_HIP_GFX906" in x for x in base))

    for tag, extra in (("base", []), ("a0", ["-I/w/isa/ov"])):
        cmd = base[:1] + extra + base[1:] + ["-S", "-o", "/w/isa/%s.s" % tag]
        p = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
        print("\n=== %s: rc=%s stderr=%d B ===" % (tag, p.returncode, len(p.stderr)))
        if p.returncode:
            print(p.stderr[-1500:])
            continue
        txt = io.open("/w/isa/%s.s" % tag, encoding="utf-8", errors="replace").read()
        print("assembly lines:", len(txt.splitlines()))
        for op in OPS:
            n = len(re.findall(r"\b" + re.escape(op) + r"\b", txt))
            if n:
                print("  %-20s %5d" % (op, n))

    # opcode histogram of the score kernel in both files
    for tag in ("base", "a0"):
        try:
            txt = io.open("/w/isa/%s.s" % tag, encoding="utf-8", errors="replace").read()
        except IOError:
            continue
        funcs, cur, buf = {}, None, []
        for ln in txt.splitlines():
            m = re.match(r"^[0-9a-f]{16} <(.+)>:$", ln)
            if m:
                if cur:
                    funcs[cur] = buf
                cur, buf = m.group(1), []
                continue
            if cur is not None:
                buf.append(ln)
        if cur:
            funcs[cur] = buf
        hits = {k: v for k, v in funcs.items() if "attn_chunk_kernel" in k and "ILi3E" in k}
        print("\n=== %s: %d attn_chunk_kernel<3,...> bodies ===" % (tag, len(hits)))
        for k in list(hits)[:2]:
            body = hits[k]
            n_dot4 = sum("v_dot4_i32_i8" in l for l in body)
            n_soft = sum(any(o in l for o in ("v_mad_i32_i24", "v_cndmask_b32", "v_perm_b32"))
                         for l in body)
            print("  %-70s lines=%5d  dot4=%3d  soft-dp4a-ops=%3d" %
                  (k[:70], len(body), n_dot4, n_soft))


if __name__ == "__main__":
    main()
