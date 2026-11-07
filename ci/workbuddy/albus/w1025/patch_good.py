#!/usr/bin/env python3
"""Add the two dependency rows to the report-gate self-test sample.

The gate now requires section 一 to carry ROCm and llama.cpp explicitly; its own positive
sample must satisfy that, otherwise round_gate reports a false red on every run.
"""
import io

P = "/home/albus/strata166/pr/strata-fork/ci/round_gate.py"
s = io.open(P, encoding="utf-8").read()
anchor = "| 8 | 本轮改动 | 零；disk = build = running 三方一致 |\n"
add = ("| 9 | ROCm 版本 | 打包 .info/version 10.1.0；HIP 7.16.26323-0000000 |\n"
       "| 10 | llama.cpp 版本 | b11062 = 3cf03257f219afbe7334045ff7c6a06ac68c627d |\n")
assert anchor in s, "GOOD sample row 8 not found"
if "| 9 | ROCm 版本" not in s:
    s = s.replace(anchor, anchor + add, 1)
io.open(P, "w", encoding="utf-8", newline="\n").write(s)
print("round_gate GOOD sample +2 rows")
