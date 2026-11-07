#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""W938: resolve rebase conflict 1/37 (901e6b0a).

qsa_select.cu     -> upstream supersedes our W842 hunk (SIMT 0/1/2 + community + alt_min_tokens): take HEAD.
arch_defaults.hpp -> both sides appended a declaration at the same spot: keep both.
"""
import io, re, subprocess, sys

W = "/home/albus/strata166/work/rebase-trial"

# 1) qsa_select.cu: take the upstream side (during a rebase --ours is the branch rebased onto)
r = subprocess.run(["git", "-C", W, "checkout", "--ours", "src/kernels/cuda/qsa_select.cu"],
                   capture_output=True, text=True)
print("checkout --ours qsa_select.cu rc=%d %s" % (r.returncode, r.stderr.strip()))
txt = io.open(W + "/src/kernels/cuda/qsa_select.cu", encoding="utf-8").read()
print("  has upstream simt_env :", "simt_env" in txt)
print("  has our W842 marker   :", "W842 local" in txt)
print("  conflict markers      :", txt.count("<<<<<<<"))

# 2) arch_defaults.hpp: concatenate ours (upstream) then theirs (our commit)
p = W + "/include/strata/core/arch_defaults.hpp"
s = io.open(p, encoding="utf-8").read()
pat = re.compile(r"<<<<<<< [^\n]*\n(.*?)=======\n(.*?)>>>>>>> [^\n]*\n", re.S)
m = pat.search(s)
if not m:
    print("FAIL: no conflict block in arch_defaults.hpp"); sys.exit(2)
ours, theirs = m.group(1), m.group(2)
merged = ours + "\n" + theirs
# a blank line between the two declaration groups
if not merged.endswith("\n"):
    merged += "\n"
s = s[:m.start()] + merged + s[m.end():]
io.open(p, "w", encoding="utf-8").write(s)
print("arch_defaults.hpp: kept both (%d + %d lines), markers left = %d"
      % (ours.count("\n"), theirs.count("\n"), s.count("<<<<<<<")))
