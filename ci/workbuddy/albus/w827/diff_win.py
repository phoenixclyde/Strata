# -*- coding: utf-8 -*-
"""拉 v0.2.7.1 / v0.2.8 两个版本的关键引擎文件，落盘并输出精简 diff。"""
import sys, os, base64, difflib
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "w820"))
from gh import api

OUT = os.path.join(os.path.dirname(__file__), "up")
os.makedirs(OUT, exist_ok=True)

FILES = [
    "src/kernels/cuda/s2_expert_grouped.cu",
    "include/strata/kernels/s2_expert_grouped.hpp",
    "include/strata/kernels/window_limits.hpp",
]

for f in FILES:
    got = {}
    for tag in ("v0.2.7.1", "v0.2.8"):
        try:
            d = api("/repos/Niko1221/Strata/contents/%s?ref=%s" % (f, tag), timeout=150)
            got[tag] = base64.b64decode(d["content"]).decode("utf-8", "replace")
        except SystemExit as e:
            print("ERR", tag, f, e); got[tag] = ""
    name = f.replace("/", "__")
    for tag, txt in got.items():
        open(os.path.join(OUT, "%s.%s" % (name, tag.replace(".", ""))), "w",
             encoding="utf-8", newline="\n").write(txt)
    A = got["v0.2.7.1"].splitlines()
    B = got["v0.2.8"].splitlines()
    d = list(difflib.unified_diff(A, B, "0271", "028", n=3, lineterm=""))
    print("=" * 70)
    print("%s   %d -> %d lines, diff %d" % (f, len(A), len(B), len(d)))
    print("\n".join(d[:110]))
