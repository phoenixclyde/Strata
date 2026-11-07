# -*- coding: utf-8 -*-
"""AUDIT24 doc: correct A24-12 (my own wrong correction) and add the remediation-state section."""
import io

p = "D:/workbuddy_space/strata_ws/deploy/AUDIT24_W900_W951.md"
s = io.open(p, encoding="utf-8").read()

old = ("| A24-12 | `W948` | 版本序判据无效：`get_J_max` **上游 master 也是 0**（只有我们 pin 有 1 处）⇒ 是自家补丁；"
       "`3cf03257` 只出现在**别人的 bench README**，不是\u201c我们的 pin\u201d ⇒「三家 fork 更旧」未被源码建立 | 横幅 + `R90` 前置 |")

new = ("| A24-12 | `W948` | ~~版本序判据无效~~ **（本条的处置本身是错的，见 §0.1）**：`get_J_max` 的有无不构成版本序；"
       "真正的锚点是 `LLAMA_VERSION` + 文件逐字节比对 ⇒ 我们 = **0.4.1 / `e6ab7c1a4`**，mx 0.6.0 与 exabit 0.7.0 **比我们新**，"
       "上游 **0.8.0** ⇒ 落后 **4 个 minor** | 已由 `W953` 改写（`W948`/`W946`/`W832` 三处） |")

n = s.count(old)
s = s.replace(old, new, 1)

add = """
### 0.1 审计输出的自我整改（本轮最重要的一条）

审完 50 件之后，机主要求「审计输出全面整改」。整改第一条就撞上**我自己写错的更正**：

`A24-12` 我采纳了 `W948` 的「版本号不是可比锚点」，并进一步断言「`get_J_max` 是我们自己的补丁」。
本轮按"正确 tag 上的来源文件"复核，两个方向都反了：

| 事实 | 证据 |
|---|---|
| 我们 = upstream **`e6ab7c1a4`（0.4.1，2026-09-22）** | `mmq.cuh` 与上游该 tag **逐字节相同（diff 0，71,851 B）**；我们 `CMakeLists.txt` 的 `LLAMA_VERSION` = 0.4.1 |
| mx 0.6.0、exabit 0.7.0 **比我们新** | 两个 tag 的 `CMakeLists.txt` 同字段 |
| 上游 master / `b12099` = **0.8.0** | 同上（`b12099` 发布于 2026-11-04T05:47:21Z） |
| `get_J_max` 是 0.4.1 时代的上游符号、后被删 | e6ab7c1a4 有 1 处，master/mx/furnace 都是 0（furnace 同基座但重写了 MMQ） |

⇒ 见 `W953`。由此立 **纪律㉕**：版本先后只能用"正确 tag 上的来源文件"证明，**不能由符号的有无推断**。

**教训**：审计也会引入错误，而且带着"更正"的名义更容易被后来者当权威引用。
所以本轮把整改做成**可机器复核**：`deploy/AUDIT_LEDGER_A24.tsv` 每条记 `id / 级别 / 文件 / 标志串 / 状态 / 处置 / md5`，
`tools/audit_closure.py` 逐条校验"标志串是否还在文档里"——**后续任何人删掉一条撤回，脚本立刻 FAIL**。

"""
if "### 0.1 审计输出的自我整改" not in s:
    s = s.replace("---\n\n## 1 P1 清单", add + "---\n\n## 1 P1 清单", 1)

io.open(p, "w", encoding="utf-8", newline="").write(s)
print("AUDIT24: A24-12 replaced", n, "| section 0.1 added", "### 0.1" in s)
