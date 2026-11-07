#!/usr/bin/env python3
"""W1039: the cost curve + the zero-code fallback into report and plan."""
import io

R = "albus/w1039/reply.md"
r = io.open(R, encoding="utf-8").read()

old4 = "**418 条 / 已结 331 / 79.2%**（本轮 +31：`P445`–`P475`）"
new4 = "**420 条 / 已结 333 / 79.3%**（本轮 +33：`P445`–`P477`）"
assert old4 in r
r = r.replace(old4, new4, 1)

para = """
**把代价算成曲线之后，结论从「短快长慢」变成「≤16K 拿满」（`P477`）**。`generate.cpp:16400-16408` 在**每个请求边界**调 `kvg_trim(n + 256, hold_on ? conversations.longest_tokens() + 256 : 0)`，而 `STRATA_KV_GROW_HOLD` 默认关 ⇒ **trim 到本请求的长度**，不是「停放的对话一直占着」。所以我先前对 `conversation_cache.hpp:260` 那句「kv-grow keeps the K/V that long while it could be restored」的担心只在 opt-in 时成立。

按 816 B/cell × 12 层 = 9,792 B/cell、全额 2.391 GiB、槽均价 2.99 MiB：

| 上下文 | KV 占 VRAM | 让给缓存 | 折合槽 |
|---|---|---|---|
| 16K | 149 MiB | 2.24 GiB | **+767** |
| 20K | 191 MiB | 2.20 GiB | +754 |
| 32K | 306 MiB | 2.09 GiB | +716 |
| 64K | 612 MiB | 1.79 GiB | +614 |
| 128K | 1.20 GiB | 1.20 GiB | +409 |
| 262K | 2.39 GiB | 0 | 0 |

**我们的典型 8K–16K 正好在满额区。** 失败模式也写在源码里：trim 失败会打印 `ERR the K/V could not give its VRAM back to the expert cache` 并退出 ⇒ 窗口里必须专门盯这一行。

**另有一条零代码的备选，我没漏（`P476`）**：`--kv-resident 4096`（作者已把下限从 20480 下调到 4096，注释称 4096/8192 在 128K、20K、8K 提示下「gave the same tokens as 20480」）把整个 K/V 放 pinned RAM、VRAM 只留 40 MiB，**让出 2.35 GiB ⇒ +804 槽**，比 kv-grow 还多一点点（因为 kv-grow 起机初始映射是 16384 cells）。**但它不省 PCIe**：超出窗口的每个 cell 都要从宿主内存流，而作者那句话只保证**输出 token 相同**、没给速度。生产典型 8K–16K 提示正好落在「要流」的区间，所以它是**备选与对照**，不是第一选择。宿主 125 GB / 可用 43 GB、`ulimit -l` unlimited ⇒ 2.39 GiB pinned 放得下。
"""
j = r.find("**顺带的旁证（与 R104 的方向一致，不是依据）**")
assert j > 0
r = r[:j] + para.lstrip("\n") + "\n" + r[j:]
io.open(R, "w", encoding="utf-8", newline="\n").write(r)
print("report: curve + fallback inserted; §四 ->", new4)

PL = "deploy/W832_OPT_PLAN_V2.md"
p = io.open(PL, encoding="utf-8").read()
p = p.replace("**418 条 / 已结 331 / 79.2%**", "**420 条 / 已结 333 / 79.3%**", 1)

anchor = "- **预期 / 代价**：起机让出 ≈2.23 GiB ⇒ 7463 → ≈8209 槽（**+10.0%**，按 2.99 MiB/槽）；代价是长请求从缓存借 chunk，**短上下文更快、长上下文回落到现值**。20K 点在采集器里专门触发一次增长。"
new = """- **预期 / 代价**：起机让出 ≈2.23 GiB ⇒ 7463 → ≈8209 槽（**+10.0%**，按 2.99 MiB/槽）。代价曲线按请求长度（`kvg_trim(n+256, 0)`，`STRATA_KV_GROW_HOLD` 默认关）：16K 时 KV 149 MiB ⇒ **+767 槽**、32K ⇒ +716、64K ⇒ +614、128K ⇒ +409、262K ⇒ 0。**典型 8K–16K 拿满。**
- **失败模式**：trim 不成 ⇒ `ERR the K/V could not give its VRAM back to the expert cache` 并退进程（窗口必看）。
- **零代码备选（`P476`）**：`--kv-resident 4096` 把整个 K/V 放 pinned RAM，VRAM 只留 40 MiB ⇒ 让出 2.35 GiB ⇒ **+804 槽**，不用 VMM、不改一行；但超窗口的 K/V 走 PCIe，作者只承诺「同样 token」不承诺速度 ⇒ **备选/对照，不是首选**。"""
assert anchor in p
p = p.replace(anchor, new, 1)
io.open(PL, "w", encoding="utf-8", newline="\n").write(p)
print("plan: §十四 curve + fallback, denom -> 420/333")
