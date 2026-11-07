#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""w861_inspect2.py -- 两件事：
 A) gfx950 新格式 logic 的 dict 结构（14 个键各叫什么）—— 作为"别家架构"的模板依据
 B) rocBLAS 自带 gfx906 的 HH 库（msgpack）能否被 hipBLASLt 的 LibraryIO 读出来
    —— 能读就直接转格式，绕开所有 logic 缺字段问题
"""
import sys

sys.path.insert(0, "/src/projects/hipblaslt/tensilelite")
import yaml  # noqa: E402
from Tensile import LibraryIO  # noqa: E402

NEW = ("/src/projects/hipblaslt/library/src/amd_detail/rocblaslt/src/Tensile/"
       "Logic/asm_full/gfx950/gfx950/Equality/"
       "gfx950_Cijk_Ailk_Bjlk_HHS_BH_BiasSH_HAS_SAV_UserArgs.yaml")

print("=== A) gfx950 新格式结构 ===")
d = yaml.safe_load(open(NEW, encoding="utf-8"))
print("type:", type(d).__name__, " n_keys:", len(d))
for k in d:
    v = d[k]
    t = type(v).__name__
    n = len(v) if hasattr(v, "__len__") else "-"
    print("  %-28s %-10s len=%s" % (k, t, n))
for k in ("Solutions", "ProblemType"):
    if k in d:
        sub = d[k]
        if isinstance(sub, list) and sub and isinstance(sub[0], dict):
            print("  %s[0] n_keys=%d" % (k, len(sub[0])))
        elif isinstance(sub, dict):
            print("  %s n_keys=%d -> %s" % (k, len(sub), list(sub)[:8]))

print()
print("=== B) rocBLAS gfx906 HH 库能否读 ===")
ROC = ("/opt/rocm/lib/rocblas/library/gfx906/"
       "TensileLibrary_Type_HH_Contraction_l_Ailk_Bjlk_Cijk_Dijk_gfx906.dat")
for fmt in ("msgpack", "yaml"):
    try:
        lib = LibraryIO.read(ROC, fmt)
        print("read as %-8s OK  type=%s" % (fmt, type(lib).__name__))
        if isinstance(lib, dict):
            print("   keys:", list(lib)[:8])
            sols = lib.get("solutions", [])
            print("   solutions:", len(sols))
        break
    except Exception as e:  # noqa
        print("read as %-8s FAIL: %s: %s" % (fmt, type(e).__name__, str(e)[:160]))
