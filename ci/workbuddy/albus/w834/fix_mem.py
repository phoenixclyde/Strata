# -*- coding: utf-8 -*-
"""重写记忆里的 W834b 段（前一次被 shell 反引号吃掉内容）。"""
import io

P = "D:/workbuddy_space/strata_ws/.workbuddy/memory/2026-10-31.md"
BLOCK = io.open("D:/workbuddy_space/strata_ws/albus/w834/mem_block.md", encoding="utf-8").read()

s = io.open(P, encoding="utf-8").read()
i = s.find("## W834b")
j = s.find("## 待办")
assert i > 0 and j > i, (i, j)

s2 = s[:i] + BLOCK + s[j:]
io.open(P, "w", encoding="utf-8", newline="\n").write(s2)
print("rewritten", len(s), "->", len(s2))
print(s2[i:i + 300])
