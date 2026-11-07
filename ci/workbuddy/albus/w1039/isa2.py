#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""W1039/P457: device-side ISA of <..,0> vs <..,16>.

The host object only carries 50-instruction stubs; the device code lives in the fatbin.  So take the exact
command build.ninja uses for this TU, swap `-c -o obj` for `--cuda-device-only -S`, and count opcodes in the
two kernel bodies.  Local, no GPU.
"""
import io
import os
import re
import subprocess
import sys

BUILD = "/out/build.ninja"
SRC = "qsa_decode_attn.cu"


def get_cmd():
    s = io.open(BUILD, encoding="utf-8", errors="replace").read()
    # find the build edge that mentions our source, then its FLAGS line
    blocks = s.split("\nbuild ")
    for b in blocks:
        if SRC + ".o" in b.split("\n")[0]:
            flags = None
            inc = ""
            for ln in b.split("\n"):
                if ln.strip().startswith("FLAGS = "):
                    flags = ln.strip()[len("FLAGS = "):]
                elif ln.strip().startswith("INCLUDES = "):
                    inc = ln.strip()[len("INCLUDES = "):]
            if flags:
                return inc + " " + flags
    return None


def main():
    flags = get_cmd()
    if not flags:
        print("FLAGS not found")
        return 2
    # drop -o and the -c, ask for device-only assembly
    flags = re.sub(r"-o\s+\S+", "", flags)
    flags = re.sub(r"(^|\s)-c(\s|$)", r"\1\2", flags)
    cmd = ("/opt/rocm/lib/llvm/bin/clang++ " + flags +
           " -x hip --cuda-device-only -S -o /w/attn_inst.s /src/src/kernels/cuda/qsa_decode_attn.cu")
    print("compiling ...")
    r = subprocess.run(["bash", "-lc", cmd], capture_output=True, text=True)
    print("rc=%d %s" % (r.returncode, r.stderr[-400:] if r.returncode else ""))
    if r.returncode:
        return 1

    txt = io.open("/w/attn_inst.s", encoding="utf-8", errors="replace").read()
    # device labels look like:  _ZN...attn_chunk_kernelILi3ELb0ELb1ELb1ELi16EEEv...
    parts = re.split(r"^(_Z[^\s:]*attn_chunk_kernel[^\s:]*):\s*$", txt, flags=re.M)
    found = {}
    for i in range(1, len(parts), 2):
        name, body = parts[i], parts[i + 1]
        m = re.search(r"ILi3ELb(\d)ELb(\d)ELb(\d)ELi(\d+)E", name)
        if not m:
            continue
        found[int(m.group(4))] = body
    print("instantiations: %s" % sorted(found))

    keys = ["global_load_dwordx2", "global_load_dwordx4", "s_mul_i32", "v_mul_lo_u32",
            "v_lshrrev_b32", "v_mul_f32", "v_fma_f32", "v_mac_f32", "v_cvt_f32_i32",
            "ds_read_b128", "ds_write_b128", "v_dot4_i32_i8", "v_dot2_f32_f16",
            "s_waitcnt", "v_add_f32", "v_pk_fma_f32"]
    for opt in (0, 16, 32, 2, 8):
        if opt not in found:
            continue
        body = found[opt]
        ops = re.findall(r"^\s+([a-z][a-z0-9_]+)\s", body, flags=re.M)
        hist = {}
        for o in ops:
            hist[o] = hist.get(o, 0) + 1
        print("\n== OPT=%d  %d instructions" % (opt, len(ops)))
        for k in keys:
            if hist.get(k):
                print("   %-20s %4d" % (k, hist[k]))
        loads = [l.strip() for l in body.split("\n") if "global_load_dwordx2" in l]
        for ln in loads[:4]:
            print("   " + re.sub(r"\s+", " ", ln)[:160])
    return 0


if __name__ == "__main__":
    sys.exit(main())
