# -*- coding: utf-8 -*-
"""AUDIT19: register A13 (compute-roof convention). Idempotent."""
p = r"D:\workbuddy_space\strata_ws\deploy\AUDIT19_ROOFLINE_REMEDIATION.md"
s = open(p, encoding="utf-8").read()
old = "| A12 | `W713_PLAN.md` 已冻结但仍在 `deploy/` 根，容易被当成权威 | P2 | `AUDIT_INDEX.md` 已标「权威方案 = `W832_OPT_PLAN_V2.md`」，本轮再确认 |"
row = ("| A13 | 算力类「占峰值」也用了规格值（`W858_THREE_LINES.md:98` 的 26.6 TFLOPS） | P2 | "
       "**不改**，但登记口径：带宽必须用实测 884；算力若要驱动决策，同样要换实测 GEMM 上限"
       "（roofline 的规矩是两个屋顶都实测）。当前该表只用于说明 prefill 远离算力屋顶，结论不受影响 |")
if "A13" in s:
    print("already registered")
else:
    assert s.count(old) == 1, s.count(old)
    s = s.replace(old, old + "\n" + row, 1)
    open(p, "w", encoding="utf-8", newline="\n").write(s)
    print("A13 registered")
