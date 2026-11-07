# -*- coding: utf-8 -*-
"""把 W775delta 长行压成精简版（保留全部 P 编号），使 MEMORY.md 回到 2900 以内。
找不到目标行就 fail-closed。"""
import io

p = r"D:/workbuddy_space/strata_ws/.workbuddy/memory/MEMORY.md"
NEW = ("- **W775delta**：P55/P56于k8v4不可达;decode需5+runs;PLE用direct(ram-45%);**W17:352/262/132**;"
       "W26:缓存=预填+adapt迁移,复放0.9564;**W28=VRAM9761/RAM33.44G/SSD22G;冷读=budget关借区;stager30/30;"
       "**W28E:IO_STATS;P54=IO_PF_STAGE;判据=blob读0**;**B8无增益;B7:借区N==M/文件0/冷读-2.5%;"
       "drop_caches不重置mmap页**")

lines = io.open(p, encoding="utf-8").read().split("\n")
idx = [i for i, l in enumerate(lines) if l.startswith("- **W775delta**")]
assert len(idx) == 1, idx
i = idx[0]
print("old len", len(lines[i]), "->", len(NEW))
lines[i] = NEW
s = "\n".join(lines)
io.open(p, "w", encoding="utf-8", newline="\n").write(s)
print("chars", len(s))
