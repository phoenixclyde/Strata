#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""W1039/P457: device ISA of the baseline instantiation vs the two diagnostic arms.

The question is narrow: does `attn_chunk_kernel<3,false,true,true,16>` compute the K address and the
64-group scale index the same way as `<...,0>`?  Print, per kernel, the global-load and index-arithmetic
instructions in order, plus a size/opcode summary.  Local, no GPU.
"""
import io
import re
import sys

PATH = "/w/code906.s"


def split_funcs(txt):
    out = {}
    cur = None
    buf = []
    for ln in txt.splitlines():
        m = re.match(r"^[0-9a-f]{16} <(.+)>:$", ln)
        if m:
            if cur:
                out[cur] = buf
            cur = m.group(1)
            buf = []
            continue
        if cur is not None:
            buf.append(ln)
    if cur:
        out[cur] = buf
    return out


def opcodes(body):
    ops = []
    for ln in body:
        if "//" in ln or ln.strip().startswith("---"):
            pass
        m = re.match(r"^\s+([a-z][a-z0-9_.]*)\s", ln)
        if m and m.group(1) not in ("s", "v", "off"):
            ops.append(m.group(1))
    return ops


def main():
    txt = io.open(PATH, encoding="utf-8", errors="replace").read()
    funcs = split_funcs(txt)
    want = {}
    for name in funcs:
        m = re.search(r"attn_chunk_kernelILi3ELb0ELb1ELb1ELi(\d+)E", name)
        if m:
            want[int(m.group(1))] = name
    print("instantiations of <3,false,true,true,*>: %s" % sorted(want))

    keys = ["v_fma_f32", "v_mac_f32", "v_mul_f32", "v_cvt_f32_i32", "v_cvt_f16_f32",
            "global_load_dwordx2", "global_load_dwordx4", "global_load_ushort", "global_load_dword",
            "ds_read_b128", "ds_write_b128", "ds_read2_b32", "v_lshrrev_b32", "s_mul_i32",
            "v_mul_lo_u32", "v_add_u32", "v_dot4_i32_i8", "v_dot2_f32_f16", "s_waitcnt"]
    for opt in (0, 2, 8, 16, 32):
        if opt not in want:
            continue
        ops = opcodes(funcs[want[opt]])
        hist = {}
        for o in ops:
            hist[o] = hist.get(o, 0) + 1
        print("\n== OPT=%d: %d instructions" % (opt, len(ops)))
        print("   " + "  ".join("%s=%d" % (k, hist[k]) for k in keys if hist.get(k)))

    # the K load: 8 bytes at p.k_q + row*256 + lane*8; the scale is a 16-bit load
    for opt in (0, 16):
        if opt not in want:
            continue
        body = funcs[want[opt]]
        print("\n---- OPT=%d: global loads (in order) ----" % opt)
        n = 0
        for ln in body:
            if "global_load" in ln:
                n += 1
                if n <= 14:
                    print("   " + re.sub(r"\s+", " ", ln.strip())[:130])
        print("   total global loads: %d" % n)


if __name__ == "__main__":
    main()
