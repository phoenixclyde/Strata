#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""W1039/P457: full opcode histogram for <..,0> vs <..,16>, plus the instructions around the score loop.

Previous pass only counted a hand-picked key list and missed `v_fmac_f32`, which is what gfx906 emits for
`fma(a,b,c)` with dst==c.  So "OPT=16 has 3 v_fma_f32" said nothing.  This prints the top opcodes of each
body and the neighbourhood of the first fma in both, so the score loop can be compared as code.
"""
import io
import re
import sys

PATH = "/w/code906.s"


def split_funcs(txt):
    out, cur, buf = {}, None, []
    for ln in txt.splitlines():
        m = re.match(r"^[0-9a-f]{16} <(.+)>:$", ln)
        if m:
            if cur:
                out[cur] = buf
            cur, buf = m.group(1), []
            continue
        if cur is not None:
            buf.append(ln)
    if cur:
        out[cur] = buf
    return out


def ops_of(body):
    res = []
    for ln in body:
        m = re.match(r"^\s+([a-z][a-z0-9_.]*)\s", ln)
        if m and m.group(1) not in ("s", "v", "off"):
            res.append(m.group(1))
    return res


def main():
    txt = io.open(PATH, encoding="utf-8", errors="replace").read()
    funcs = split_funcs(txt)
    want = {}
    for name in funcs:
        m = re.search(r"attn_chunk_kernelILi3ELb0ELb1ELb1ELi(\d+)E", name)
        if m:
            want[int(m.group(1))] = name

    for opt in (0, 16):
        if opt not in want:
            print("OPT=%d missing" % opt)
            continue
        body = funcs[want[opt]]
        ops = ops_of(body)
        hist = {}
        for o in ops:
            hist[o] = hist.get(o, 0) + 1
        print("\n===== OPT=%d : %d instructions =====" % (opt, len(ops)))
        for k, v in sorted(hist.items(), key=lambda kv: -kv[1])[:18]:
            print("   %-24s %5d" % (k, v))
        # first float-fma neighbourhood
        print("   --- around the first v_fma/v_fmac ---")
        for i, ln in enumerate(body):
            if "v_fma_f32" in ln or "v_fmac_f32" in ln:
                for l in body[max(0, i - 6):i + 10]:
                    print("     " + re.sub(r"\s+", " ", l.strip())[:120])
                break


if __name__ == "__main__":
    main()
