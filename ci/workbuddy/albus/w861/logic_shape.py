#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""w861_logic_shape.py -- 旧 logic 文件的元素结构（判断 6 元素 vs 12 元素代差）"""
import sys
import yaml

d = yaml.safe_load(open(sys.argv[1], encoding="utf-8"))
print("top len =", len(d))
for i, e in enumerate(d):
    t = type(e).__name__
    n = len(e) if hasattr(e, "__len__") else "-"
    print("  [%d] %-5s len=%s" % (i, t, n))
if isinstance(d[5], list) and d[5] and isinstance(d[5][0], dict):
    ks = list(d[5][0].keys())
    print("solution[0] n_keys=%d" % len(ks))
    print("  underscore keys:", [k for k in ks if k.startswith("_")][:10])
    print("  first 12 keys:", ks[:12])
