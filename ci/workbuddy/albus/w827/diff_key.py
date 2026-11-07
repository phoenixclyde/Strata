# -*- coding: utf-8 -*-
"""对关键引擎文件做 diff，只打印与 HIP/AMD/gfx906/缓存/窗口/verify 相关的行。"""
import sys, os, base64, difflib, re

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "w820"))
from gh import api

OUT = os.path.join(os.path.dirname(__file__), "up")
os.makedirs(OUT, exist_ok=True)

FILES = [
    "include/strata/core/conversation_cache.hpp",
    "src/core/expert_source.cpp",
    "src/core/verify.cpp",
    "src/kernels/cuda/verify_kernels.cu",
]

KEY = re.compile(r"HIP|AMD|gfx|__HIPCC__|reserve|park|prefix|cache|window|MAX_T|auto", re.I)

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
    d = list(difflib.unified_diff(A, B, "0271", "028", n=1, lineterm=""))
    body = [x for x in d if x.startswith(("+", "-")) and not x.startswith(("+++", "---"))]
    hits = [x for x in body if KEY.search(x)]
    print("=" * 72)
    print("%s   %d -> %d lines | +-%d | 命中关键词 %d 行" % (f, len(A), len(B), len(body), len(hits)))
    for x in hits[:36]:
        print("   " + x[:175])
