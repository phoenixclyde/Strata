# -*- coding: utf-8 -*-
"""修回 W828 §6.15 被 shell 反引号吃掉的那段（改用文件方式写，内容里带反引号也安全）。"""
import io

P = "D:/workbuddy_space/strata_ws/deploy/W828_UPSTREAM_028_PORT.md"
s = io.open(P, encoding="utf-8").read()

START = "⇒ **结论：这 1.2 s 的构成在 0.1.54 上无法判定**"
END = "（**这条已在 §6.16 解开**"
i = s.find(START)
j = s.find(END)
assert i > 0 and j > i, (i, j)

NEW = """⇒ **结论：这 1.2 s 的构成在 0.1.54 上无法判定**，因为当时只查到 decode 的相位表（`STRATA_DECODE_TIMING`）。

> **W834 更正（2026-10-31）**：上面这句是错的 —— **prefill 侧有计数器**。
> `src/prefill/prefill.cpp:2731` 起定义了 `STRATA_PREFILL_TIMING=1`，打 **21 个相位**：
> embed+steps / hc read / gdn / qsa proj / qsa indexer / qsa select / qsa attn / router+shared /
> **host grouping** / gather / **wait copy** / dequant / gemm gate/up / gemm down / combine / ple /
> kv stage / gdn conv+gates / gdn recurrence / gdn out proj / hc write，
> 并额外记 host 侧 `sync` / `chunk` / `setup` 三项。
> ⇒ 这 1.2 s **不需要改源码就能分解**，当时只是 grep 的范围漏了 `src/prefill/`。

能确定的只有：**它随数学路径变化 ⇒ 与算力有关；它不随长度变化 ⇒ 是 chunk 级常数。**

"""

s2 = s[:i] + NEW + s[j:]
io.open(P, "w", encoding="utf-8", newline="\n").write(s2)
print("ok", len(s), "->", len(s2))
print(s2[i:i + 620])
