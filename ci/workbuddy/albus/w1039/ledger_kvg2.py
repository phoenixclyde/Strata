#!/usr/bin/env python3
"""W1039/R104: the zero-code alternative (--kv-resident) and kv-grow's real cost curve."""
import io

P = "deploy/PROGRESS.tsv"
CELL = 816 * 12            # bytes per cell across the 12 QSA layers (k8v4)
SLOT = 21.79 * 1024 / 7463  # MiB per slot, measured: 21.79 GiB / 7463
FULL = CELL * 262144 / 2**30  # GiB

rows = []
curve = []
for cells, label in ((16384, "16K"), (20480, "20K"), (32768, "32K"), (65536, "64K"),
                     (131072, "128K"), (262144, "262K")):
    gib = CELL * cells / 2**30
    freed = FULL - gib
    slots = int(freed * 1024 / SLOT)
    curve.append("%s: KV %.2f GiB → 让出 %.2f GiB ⇒ +%d 槽" % (label, gib, freed, slots))
print("FULL KV = %.3f GiB, slot = %.2f MiB" % (FULL, SLOT))
for c in curve:
    print("  " + c)

rows.append(
    ("B1参数轴", "P476",
     "零代码备选 `--kv-resident`：同一笔显存、不用 VMM、也不用改一行；代价是超出窗口的 K/V 走 pinned RAM（PCIe），作者只承诺「同样 token」，没承诺同样速度",
     "W1039", "count", "1", "1", "OPEN",
     "**源码**：`--kv-resident N` 每个 QSA 层在 VRAM 里留 N 个 cell，**整个 K/V 放 pinned RAM**，省下的 VRAM 给专家缓存（`generate.cpp:1061` 帮助文本；`layer.cpp:743 kv_plan()` 把 `slots` 从 pages 改成窗口页数）。"
     "**窗口下限已被作者从 20480 下调到 4096**（`layer.cpp:774` 注释：4096 与 8192 在 128K/20K/8K 提示下「gave the same tokens as 20480」）。"
     "**算出来的收益（按 816 B/cell × 12 层、槽均价 2.99 MiB）**：窗口 4096 cells ⇒ VRAM 里只留 40 MiB，让出 **2.35 GiB ⇒ +804 槽**（略优于 kv-grow 的 +767，因为 kv-grow 的起机初始映射是 16384 cells）。"
     "**代价（这才是它不能当第一选择的原因）**：超过窗口的每个 cell 的 K/V 读都要过 PCIe；作者那句话只保证**输出 token 相同**，没有给速度。生产 `--prompt-cache-every 8192`、典型 8K–16K 提示，正好落在「要流」的区间。"
     "**用途**：kv-grow 若在窗口里失败（增长/归还出错），这是零代码落点；也是「KV 到底该占多少 VRAM」的对照臂。宿主机 125 GB / 可用 43 GB、`ulimit -l` unlimited ⇒ 2.39 GiB pinned 放得下。",
     "P444;P474", "KW:kv-resident|pinned RAM|804"))

rows.append(
    ("B1参数轴", "P477",
     "kv-grow 的真实代价曲线比「借了就少」轻得多：默认每次请求结束就 trim 回本请求长度（`STRATA_KV_GROW_HOLD` 关），**16K 上下文只占 149 MiB，仍让出 2.24 GiB ≈ +767 槽**；只有 128K 以上才减半",
     "W1039", "count", "1", "1", "DONE",
     "**源码**：`generate.cpp:16400-16408` 在请求边界调 `kvg_trim(n + 256, hold_on ? conversations.longest_tokens() + 256 : 0)`，`STRATA_KV_GROW_HOLD` 默认关 ⇒ **trim 到本请求长度**，不是「停放的对话还占着」。"
     "所以 `conversation_cache.hpp:260` 那句「kv-grow keeps the K/V that long while it could be restored」只在 opt-in 时成立——我先前担心的「停放对话把槽钉死」不成立。"
     "**曲线（816 B/cell × 12 层 = 9792 B/cell，全额 2.391 GiB，槽均价 2.99 MiB）**：16K 149 MiB → +767；20K 191 MiB → +754；32K 306 MiB → +716；64K 612 MiB → +613；128K 1.22 GiB → +409；262K 2.391 GiB → +0。"
     "⇒ **我们的工作负载（≤16K）拿满，只有极长上下文才回落**，这比「短快长慢」的粗描述准确得多。"
     "**失败模式（必须知道）**：trim 失败会打印 `ERR the K/V could not give its VRAM back to the expert cache` 并结束进程 ⇒ 窗口里要专门看这一行。",
     "P474", "KW:trim|代价曲线|767"))

lines = io.open(P, encoding="utf-8").read().splitlines()
for r in rows:
    assert len(r) == 11
    lines.append("\t".join(r))
io.open(P, "w", encoding="utf-8", newline="\n").write("\n".join(lines) + "\n")
print("appended", ", ".join(r[1] for r in rows))
