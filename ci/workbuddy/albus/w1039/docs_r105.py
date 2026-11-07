import io

R = "albus/w1039/reply.md"
r = io.open(R, encoding="utf-8").read()

old4 = "**422 条 / 已结 335 / 79.4%**（本轮 +35：`P445`–`P479`）"
new4 = "**424 条 / 已结 337 / 79.5%**（本轮 +37：`P445`–`P481`）"
assert old4 in r
r = r.replace(old4, new4, 1)

section = """
**24. `R105`：不是「gfx906 硬件少什么」，是这棵树在 gfx906 上**不定义** `STRATA_USE_HIP`（`P480`/`P481`）**

`vmm.cpp` 那条门被探针一秒推翻之后，我把它当样本去数同形状的条件：全树 93 处 `STRATA_HIP_GFX906`。数到根上发现一件比 93 更根本的事——

```
$ grep -o "DSTRATA_USE_HIP[=0-9]*" build.ninja | sort | uniq -c
      1 DSTRATA_USE_HIP=1
$ grep -n -B1 "DSTRATA_USE_HIP=1" build.ninja | grep "build "
build CMakeFiles/strata_engine.dir/src/core/dflash2.cpp.o: ...
```

**全构建只有 `dflash2.cpp` 一个 TU 定义它。** `vmm.cpp` / `mtp.cpp` / `verify.cpp` / `generate.cpp` / `prefill.cpp` 的 DEFINES 都只有 `-DSTRATA_HIP_GFX906=1`。所以「HIP 但排除 gfx906」那七处是**双死**：`defined(STRATA_USE_HIP)` 已为假，`!defined(STRATA_HIP_GFX906)` 在本构建里纯属冗余——这也正是 v1 补丁「编了个寂寞」的原因（`P473`）。

七处逐条分类见 `albus/w1039/GFX906_GATES.md`，三类：

| 类别 | 处 | 处置 |
|---|---|---|
| **假设** | `vmm.cpp:158/167`（VMM）、`generate.cpp:3078/3371`（`prime_hw_queues`） | VMM 已推翻并建候选；queue-prime 的机制（loader 线程竞态开 HW 队列，一半启动把两条忙队列排到同一 pipe）**与卡无关** |
| **可选开关被编译掉** | `mtp.cpp:486`（`STRATA_MTP_HIP_PRIO`）、`verify.cpp:1213`（`STRATA_COPY_HIP_PRIO`） | 默认本就只对 gfx12 开 ⇒ **解开不改默认**，只让开关可用 |
| **不是缺口** | `prefill.cpp:2871`（CPU share 默认值）、`verify.cpp:4`（头文件） | 我们显式设了 `STRATA_PREFILL_CPU_SHARE`，默认走不到 |

反方向也记了一笔：`verify.cpp:2210` 的 `moe_route_window` 是**专门为 gfx906 写**的整窗 router（256 专家一次 BF16 投影 + 一次 top-k，与逐 token bitwise 相同，2×MI50 上 ~55 ms 窗口里省 3 ms）。⇒ 这块是维护过的，「gfx906 落后」这个默认假设不成立。

**顺手做了一个候选（`P481`）**：把三处可选开关从编译期排除里解开，得到 `hipk` = `67ab8836` / 43,219,064 B（比 `kvg` +4,088 B），BLD=0 / FAILED=0。判据照 `P473`：`strings` 计数——在产 `b12180` 与 `kvg` 是 `MTP_PRIO=0 COPY_PRIO=0 QUEUE_PRIME=0`，`hipk` 是 **`1 / 1 / 3`**。构建完 `git checkout` 三个文件再重编，`/out` 逐位回到 `a85743d7`（= `kvg`）⇒ 树干净、`kvg` 可复现。**未装机。**

它给的是三个可单测的旋钮，而不是一次赌三件事：`STRATA_MTP_HIP_PRIO=1`（草稿流独占高优先级队列，外证 R9700 draft wall 5.8→3.5 ms/窗）、`STRATA_COPY_HIP_PRIO=1`、`STRATA_HIP_QUEUE_PRIME=nn`（**可能正是「重启后第一个请求偏慢」的机制**）。
"""
r = r.rstrip() + "\n" + section + "\n"
r = r.replace("`ab_kvg.py` / `window_kvg.sh`。", "`ab_kvg.py` / `window_kvg.sh` / `GFX906_GATES.md` / `patchA_hip_knobs.py` / `build_hipk.sh`。", 1)
io.open(R, "w", encoding="utf-8", newline="\n").write(r)
print("report §24 added; §四 ->", new4)
