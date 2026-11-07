#!/usr/bin/env python3
"""W1039: land the VMM finding in the report + the plan (§0.1 + a write-back section)."""
import io
import re

REPORT = "albus/w1039/reply.md"
PLAN = "deploy/W832_OPT_PLAN_V2.md"

# ---------- report: four-part block + a new body section ----------
r = io.open(REPORT, encoding="utf-8").read()

old4 = "**四、进度** — **414 条 / 已结 327 / 79.0%**（本轮 +27：`P445`–`P471`）。"
new4 = "**四、进度** — **417 条 / 已结 330 / 79.1%**（本轮 +30：`P445`–`P474`）。"
assert old4 in r
r = r.replace(old4, new4, 1)

old3 = "；**重启 15 次、停机 3993 s、回滚 0 次、装机 0 次**。"
new3 = ("；本回合 **重启 0 次 / 停机 0 分钟 / 装机 0 / 回滚 0**（VMM 探针与生产共用 GPU 约 1 秒、不启引擎）；"
        "**重启 15 次、停机 3993 s、回滚 0 次、装机 0 次**。")
assert old3 in r
r = r.replace(old3, new3, 1)

# the §2 line has a bin count and md5 trio; refresh the count only (56 now)
r = r.replace("`/data/bin` **55 件**", "`/data/bin` **56 件**", 1)

section = """
**23. R104 的前提被一行源码推翻：`--kv-grow` 在 gfx906 上是「编译期被关掉」，不是硬件不支持（`P472`–`P474`）**

按队列做 `R104`（`--kv-grow`，把 K/V 从 2.391 GiB 全额预分配改成按需，让出 ≈770 槽）。第一件事不是开窗，是核前置条件——`generate.cpp:6704` 的 `on` 有**十一项**与关系：

```
asked && !multi_gpu && kv_resident <= 0 && !expert_profile.empty() && !resident_cpu_experts
      && expert_cache != 0 && !remote && vmm_available() && batch == 0 && !vram_elastic && peer_device < 0
```

生产 37 args / 9 env 逐项对：单卡 ✓、无 `--kv-resident` ✓、`--expert-profile /src/data/expert-profile.bin` ✓、无 `--resident-cpu-experts` ✓、`auto` 缓存 ✓、无 `--batch` ✓、无 `--vram-elastic` ✓、无 `--peer-device` ✓。**唯一为假的是 `vmm_available()`**，而它在 gfx906 上恒为 `false`：

```
src/core/vmm.cpp:167   #if defined(STRATA_USE_HIP) && !defined(STRATA_HIP_GFX906) && HIP_VERSION_MAJOR >= 6
src/core/vmm.cpp:299-303   #else   bool vmm_available() { return false; }
```

那句排除自带理由：`Everything else (Metal, gfx906, ROCm older than 6): no virtual memory`。**这是一个撰写时的假设，可以直接测。**

**测法沿用本轮已经证明有效的那条路：独立 HIP 探针，几十 KB，1 秒 GPU，不启引擎、不动 config。** 结果（`albus/w1039/t_vmm.cu`）：

| 步骤 | 结果 |
|---|---|
| `hipDeviceAttributeVirtualMemoryManagementSupported` | **1** |
| 最小粒度 | **4096 B**（与注释里 gfx1201 同款，代码本来就会向上取到 2 MiB） |
| `hipMemAddressReserve` 64 MiB / `hipMemCreate` / `hipMemMap` / `hipMemSetAccess` | 全部 `hipSuccess` |
| chunk 0 写读、chunk 1 增长到同 range 另一偏移后写读、chunk 0 仍完整 | **全部 mismatch=0** |
| **unmap+release chunk 0 后 chunk 1 仍完整** | **OK** ← 这正是 `--kv-grow` 需要的「把 chunk 还给专家缓存」 |

⇒ **gfx906 支持 VMM。** 那行排除是保守，不是事实。

**改一行，但第一次改动「编了个寂寞」（`P473`）。** v1 只是把 `&& !defined(STRATA_HIP_GFX906)` 去掉，重编 **BLD=0 / FAILED=0，而 md5 仍是 `d24f8293`（与在产 b12180 位相同）**。查 `build.ninja` 才知道这个 TU 的 `DEFINES` 里**没有 `-DSTRATA_USE_HIP`**，只有 `-DSTRATA_HIP_GFX906=1` ⇒ 条件仍为假，stub 又编了一遍。v2 写成 `(defined(STRATA_USE_HIP) || defined(STRATA_HIP_GFX906))` 才真的换掉实现：`a85743d7` / 43,214,976 B。**这是 `P425`/`P441`/`P446` 之后同族第四次「改的东西没在跑」**，代价 2 分钟——因为判据是「二进制变了吗」，不是「编译过了吗」。

**候选件 `strata-0.1.57-kvg` 的静态证据（不只是编过）**：动态符号表里 `hipMemAddressReserve` / `hipMemCreate` / `hipMemMap` / `hipMemSetAccess` 各 1 条，`elastic K/V` 字符串 7 条；在产 `b12180` 里 `hipMemAddressReserve` **0 条**。构建口径与在产完全一致（`/src = pr/k10 @ fa8e6761`、`/out = build-masterp`、`/llama.cpp = llama-master`）。

**预期收益（算得出来，不是拍的）**：k8v4 = 816 B/cell × 262144 cells × 12 层 = 2.391 GiB；`STRATA_KV_GROW_INIT` 默认 16384 cells ⇒ 起机只 map ≈160 MiB，让出 **≈2.23 GiB**；槽均价 = 21.79 GiB / 7463 = **2.99 MiB** ⇒ **+746 槽，7463 → ≈8209（+10.0%）**。这与我 08:39 那次实测的「KV 多 720 MiB ⇔ 槽少 240」是同一把尺子（比值 2.99 MiB/槽 一致）。

**但代价面必须一起测**：`--kv-grow` 的做法是「请求变长时，从专家缓存借 chunk，短请求时再还」。所以 `R104` 不是单纯 +10%，而是**「短上下文更快、长上下文回落到现在」**。采集器因此加了 20K 点（> init 16384），强制触发一次增长，看它是否真的从缓存拿 chunk、有没有 `could not map`。
"""
r = r.rstrip() + "\n" + section + "\n"

# refresh the artifacts paragraph
r = r.replace("`build_probe.sh` / `build_probe2.sh` / `isa4.py`。",
              "`build_probe.sh` / `build_probe2.sh` / `isa4.py` / `t_vmm.cu` / `vmm_gfx906_patch2.py` / `build_kvg.sh` / `ab_kvg.py` / `window_kvg.sh`。", 1)
io.open(REPORT, "w", encoding="utf-8", newline="\n").write(r)
print("report: §四 %s, §三 +1 clause, §23 added (%d chars)" % (new4.split("（")[0], len(section)))

# ---------- plan: §0.1 denominator + the queue line's R104 state ----------
p = io.open(PLAN, encoding="utf-8").read()
p = p.replace("**414 条 / 已结 327 / 79.0%**", "**417 条 / 已结 330 / 79.1%**", 1)

anchor = "**唯一队列** | **R104（置顶"
assert anchor in p
p = p.replace(anchor,
              "**唯一队列** | **R104（进行中，`P472`–`P474`：VMM 已证可用、候选 `kvg` 已建、待窗口）** → 原条目：" + anchor.split("| ")[1], 1)

# a write-back block, so the conclusion lives in the plan and not only in the round folder
block = """
---

### 回写 · W1039 §十四（R104：`--kv-grow` 的前置条件被实测改写）

- **判据**：`--kv-grow` 的十一项前置条件里，`vmm_available()` 是唯一为假的一项；它在 gfx906 上为假的原因是 `vmm.cpp:167` 的编译期排除，不是硬件能力。**判据 = 探针实测**，不是读注释。
- **实测（`albus/w1039/t_vmm.cu`，1 s GPU、零停机）**：属性 1、粒度 4096 B、reserve/create/map/setaccess 全 `hipSuccess`、增长与归还 chunk 全对。
- **改动面**：`src/core/vmm.cpp` 两处条件从 `STRATA_USE_HIP && !STRATA_HIP_GFX906` 改为 `STRATA_USE_HIP || STRATA_HIP_GFX906`。**运行时属性检查保留**（硬件不支持就自动退回 stub，fail-closed）。
- **踩到的坑**：该 TU 的 `DEFINES` 没有 `-DSTRATA_USE_HIP`，第一次改完 md5 不变（`P473`）。**条件编译类改动的判据是「二进制变了」**：`nm -D | grep hipMemAddressReserve`，新件 1 条、在产 0 条。
- **候选**：`strata-0.1.57-kvg` = `a85743d7f554159e8ac1e2d432d2e5ea` / 43,214,976 B，源 = `pr/k10 @ fa8e6761` + 该补丁，构建口径同 b12180。
- **预期 / 代价**：起机让出 ≈2.23 GiB ⇒ 7463 → ≈8209 槽（**+10.0%**，按 2.99 MiB/槽）；代价是长请求从缓存借 chunk，**短上下文更快、长上下文回落到现值**。20K 点在采集器里专门触发一次增长。
- **停机**：窗口两次重启（装机 + 还原），每次 ≈45 s，**合计 ≈90–100 s 不可用**；还原件 `b12180`（`d24f8293`），config 有逐字节备份（`5e9b81e2`）。
"""
p = p.rstrip() + "\n" + block
io.open(PLAN, "w", encoding="utf-8", newline="\n").write(p)
print("plan: §0.1 denom + queue state + 回写 · W1039 §十四")
