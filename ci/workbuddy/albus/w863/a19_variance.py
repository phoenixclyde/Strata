# -*- coding: utf-8 -*-
"""AUDIT19: record that the roof itself varies run to run (884 vs 803), and that the
conclusions are insensitive to which end you use. Idempotent."""
import io

A19 = r"D:\workbuddy_space\strata_ws\deploy\AUDIT19_ROOFLINE_REMEDIATION.md"
W832 = r"D:\workbuddy_space\strata_ws\deploy\W832_OPT_PLAN_V2.md"

# ---------------- AUDIT19 ----------------
s = open(A19, encoding="utf-8").read()
anchor = "拷贝屋顶（读+写都计入）：**751.6 GB/s**。"
add = """拷贝屋顶（读+写都计入）：**751.6 GB/s**。

**同一脚本第二次跑（19:0x，生产仍在服务）：读 803.2 GB/s（78.4%）、拷贝 718.3 GB/s。**
⇒ **屋顶本身有约 9% 的跑间差**（884 vs 803）。这不是探针不稳，是"可达带宽"随卡上负载/温度浮动——
和 tok/s 的 CV 是同一类现象。所以：

| 用法 | 取哪个值 | 理由 |
|---|---|---|
| 报"我们离屋顶多远" | **803–884 的区间**，不报单点 | 单点会被当成精确值，而这轮已经吃过一次亏 |
| 判"还有没有headroom" | **取 884（乐观端）** | 若在乐观屋顶下都只有 30%，结论更硬 |
| 结论是否受跑间差影响 | **不受** | 884→803 只让 dense 从 29.8% 变 32.8%、HC 从 11.1% 变 12.2%、最好的 kernel 从 53% 变 58%——**全部落在同一档** |"""
assert s.count(anchor) == 1, s.count(anchor)
if "第二次跑" not in s:
    s = s.replace(anchor, add, 1)
    open(A19, "w", encoding="utf-8", newline="\n").write(s)
    print("AUDIT19: variance note added")
else:
    print("AUDIT19 already has it")

# ---------------- W832 ----------------
t = open(W832, encoding="utf-8").read()
old = "**分母（AUDIT19 §1，实测，2026-11-01）**：这卡的**读屋顶 = 884 GB/s**（86.3% 规格，STREAM 探针 `ci/probe/stream_roof.cpp`），"
new = ("**分母（AUDIT19 §1，实测，2026-11-01）**：这卡的**读屋顶 = 803–884 GB/s**（两次实测：78.4% / 86.3% 规格；"
       "STREAM 探针 `ci/probe/stream_roof.cpp`）。下表按**乐观端 884** 算，所以是**保守**的离屋顶距离：")
if "803–884" not in t:
    assert t.count(old) == 1, t.count(old)
    t = t.replace(old, new, 1)
    open(W832, "w", encoding="utf-8", newline="\n").write(t)
    print("W832: denominator updated to the measured range")
else:
    print("W832 already has the range")
