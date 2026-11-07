#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""W1039/P457: what did the compiler actually emit for <..,0> vs <..,16>?  Local, no GPU, no window.

Both kernels live in the same translation unit, so one compile gives both.  Print, per instantiation,
the opcode histogram of the body plus the operand shape of the K load, so "the source says the same
thing" stops being the argument.
"""
import io
import re
import subprocess
import sys

VIS = "gfx906"


def main():
    obj = sys.argv[1]
    dis = subprocess.run(
        ["/opt/rocm/lib/llvm/bin/llvm-objdump", "-d", "--mcpu=" + VIS, "--demangle", obj],
        capture_output=True, text=True).stdout
    # split into functions
    funcs = {}
    cur = None
    for ln in dis.splitlines():
        m = re.match(r"^[0-9a-f]{16} <(.+)>:$", ln)
        if m:
            cur = m.group(1)
            funcs[cur] = []
            continue
        if cur is not None:
            funcs[cur].append(ln)
    want = {}
    for name in funcs:
        if "attn_chunk_kernel" not in name:
            continue
        m = re.search(r"attn_chunk_kernel<(\d+), (?:true|false), (?:true|false), (?:true|false), (\d+)>", name)
        if m and m.group(1) == "3":
            want["OPT=" + m.group(2)] = name
    print("instantiations found: %d" % len(want))
    for tag in sorted(want):
        body = funcs[want[tag]]
        ops = []
        for ln in body:
            m = re.search(r"\t([a-z][a-z0-9_]+)\s", ln)
            if m:
                ops.append(m.group(1))
        hist = {}
        for o in ops:
            hist[o] = hist.get(o, 0) + 1
        print("\n== %s  (%d instructions)  %s" % (tag, len(ops), want[tag][:90]))
        keys = ["global_load_dwordx2", "global_load_dwordx4", "s_mul_i32", "v_mul_lo_u32",
                "v_lshrrev_b32", "v_mul_f32", "v_fma_f32", "v_mac_f32", "v_cvt_f32_i32",
                "v_cndmask_b32", "ds_read_b128", "ds_write_b128", "v_dot4_i32_i8", "v_dot2_f32_f16",
                "s_waitcnt", "v_add_f32"]
        for k in keys:
            if hist.get(k):
                print("   %-20s %4d" % (k, hist[k]))
        other = sum(v for k, v in hist.items() if k not in keys)
        print("   %-20s %4d" % ("(others)", other))
        # the K load: show every global_load_dwordx2 with its offset operand
        loads = [ln.strip() for ln in body if "global_load_dwordx2" in ln]
        print("   K-load candidates: %d, first 3:" % len(loads))
        for ln in loads[:3]:
            print("      " + re.sub(r"\s+", " ", ln)[:150])


if __name__ == "__main__":
    main()
