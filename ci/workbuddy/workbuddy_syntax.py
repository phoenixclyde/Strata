#!/usr/bin/env python3
"""Syntax-check every copied WorkBuddy script without importing it."""
from __future__ import annotations

import pathlib
import py_compile
import subprocess
import sys

ROOT = pathlib.Path(__file__).resolve().parent
FAIL = []
py_files = sorted(ROOT.rglob("*.py"))
sh_files = sorted(ROOT.rglob("*.sh"))
for p in py_files:
    try:
        py_compile.compile(str(p), doraise=True)
    except Exception as e:
        FAIL.append(f"{p.relative_to(ROOT)}: {e}")
for p in sh_files:
    r = subprocess.run(["bash", "-n", str(p)], stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)
    if r.returncode != 0:
        FAIL.append(f"{p.relative_to(ROOT)}: {r.stdout.strip()[:160]}")
print(f"WORKBUDDY_SYNTAX py={len(py_files)} sh={len(sh_files)}")
if FAIL:
    print(f"WORKBUDDY_SYNTAX: FAIL ({len(FAIL)})")
    for x in FAIL[:80]:
        print("  -", x)
    raise SystemExit(1)
print("WORKBUDDY_SYNTAX: PASS")
