# W775delta · 上游 0.1.45 / 0.2.0-beta 速评（2026-10-20）

> **触发**：机主给 `https://github.com/Niko1221/Strata/releases`。
> **取证**：GitHub Releases API（12 条）· 两条 release note 全文（`deploy/tmp/_rel_v0_1_45.md` / `_rel_v0_2_0-beta.md`）· 资产清单 · 我方 4 条提交的当前状态 · 生产 `/metrics` 实读。
> **对照基线**：我们生产 = **0.1.42**（config md5 `ff8cb97379f0bdbe76ee555da6d8729c`）。

---

## 0 三句话

1. 上游 4 天内又发两版：**0.1.45（10-17）** 与 **0.2.0-beta（10-19）**；0.2.0 是**产品形态重构**（app + Terminal + 分离的 engine 包，引擎包版本 **0.1.45.3**）。
2. **0.2.0-beta 明确不是给我们的**：33 个资产里 **没有任何 gfx906 / MI50 目标**（只有 hip-halo / hip-rx7900 / hip-rx9070 / cuda / metal）。
3. **10-19 上游重置了 tracker**，把我们的 **2 条 PR + 2 条 issue 全关了** —— 但关闭语逐字写着 **"Closed here does not mean rejected."**，并给了 4 步 reopen 配方。

---

## 1 时间线（UTC）

| 时刻 | 事件 |
|---|---|
| 2026-10-17T06:53Z | **v0.1.45** 发布（4 个资产，无 gfx906） |
| 2026-10-19T13:52Z | **v0.2.0-beta** 发布（33 个资产，无 gfx906） |
| 2026-10-19T15:18:06Z | 我方 issue **#1923** 关为 `not_planned` |
| 2026-10-19T15:18:12Z | 我方 issue **#1926** 关为 `not_planned` |
| 2026-10-19T16:56:38Z | 我方 PR **#1855**（bench）关闭 |
| 2026-10-19T16:57:31Z | 我方 PR **#1877**（Monitor FRU）关闭 |

关闭评论全文（四条同一模板，`#1877` 逐字）：

> Thanks for the pull request.
> We're resetting the tracker for 0.2.0-beta. There are more than **1,300 open issues and pull requests**, too many for us to review properly, so we're closing everything that isn't being worked on right now. **Closed here does not mean rejected.**
> To reopen it takes about two minutes:
> 1. Rebase on `main` if it no longer applies, and re-run your checks on 0.2.0-beta.
> 2. Start the title with its area: `[Engine]`, `[GUI]`, `[TUI]`, `[Benchmark]`, `[Docs]` or `[Other]`.
> 3. Fill in the pull request template: the problem and result, and the validation (what you ran, on which revision, what you saw).
> 4. Comment `/reopen`. A check runs and either reopens the pull request or lists what is still missing.

=> **这不是否决，是"清场 + 立规矩"**。我们的两条 PR 都在可复活面内，代价是**按新模板重做**。

---

## 2 0.2.0-beta 是什么（对我们的意义）

**形态**：拆成三件 —— **app**（Win/Linux/Mac GUI）· **Terminal**（`strata launch` / `connect` / `models` / `update` / `doctor` / `bench run`）· **engine**（按平台+卡种分发的独立包，版本 **0.1.45.3**，签名 feed + 逐文件校验 + 试启动 + 失败回滚）。

**资产矩阵（实读 33 个）**：

| 目标 | 有无 gfx906 |
|---|---|
| `linux-nvidia-cuda12/13` | - |
| `linux-amd-rx9070`（gfx12） | - |
| `linux-amd-rx7900`（gfx11） | - |
| `linux-amd-strixhalo`（gfx1151） | - |
| `macos-arm64-metal` | - |
| **gfx906 / MI50** | **无** |

**两条对我们有直接风险的条目**：

1. **"Pictures are on by default on NVIDIA and AMD cards. 读图器在 <24 GB 卡上走 CPU；**24 GB 及以上走 GPU**；GPU 读图器占 **1,470 MiB VRAM**。"** 我们是 32 GB 卡 ->  默认会走 GPU ->  **吃掉 1.47 GB**。而生产当前 `vram_free_mib = 574`（`/metrics` 实读）->  会直接挤掉约 500 个专家槽。**若将来用 0.2.0，必须显式 `--vision cpu`。**
2. **"Docker images are not published yet; build them yourself"** ->  我们"自建镜像"这条路在 0.2.0 上仍是唯一路，且官方不给背书。

---

## 3 0.1.45 里与我们实质相关的条目

### 3.1 好事：Qwen3.8-Flash-Next 的答案不变（逐字）

> Answers of the Qwen3.8-Flash-Next models are the same as in 0.1.44.1 (**byte-identical** in our identity tests on every GPU machine we tested: CUDA sm_60 / sm_86, **HIP gfx1201**, Intel A750, Mac M4).

**注意两点**：(a) 我们的模型族被逐字保证答案不变；(b) **identity gate 的 HIP 只覆盖 gfx1201，没有 gfx906** ->  对我们只是"没有反证"，不是背书。

### 3.2 **直接打到我们 B7 冷路径的一条**：#1896 借区保留

> **A resident-RAM copy keeps the prompt path's lend region (#1896 elightcap).** With room in the RAM budget, decode went 7% and prompt reading 2.5% faster on an RTX 3060 (5 of 5 pairs).

这正是我们 W28/W28E 诊断过的那个面（"冷读主因 = budget 关借区 / 借区无 RAM 副本"）。
- 我们后来用 **B7 `--resident-experts`** 绕开了它（现役 `借区 N==M`、`files 0 blobs`），所以**这条对我们的现状可能是空操作**；
- 但它同时说明：**我们当初的归因是对的，上游独立修了同一处** —— 若将来回到 budget 模式，这条就是必需项。
- **待核**：该修复是否只在 budget 模式生效、在 `--resident-experts` 下是否有行为变化（需 0.1.45 源码，本地无）。

### 3.3 可能有用但需核：AMD 长上下文内核

> **Long prompts on AMD (#1749 vlupilin, #1943 2jztricks).** The top-k kernel for very long contexts and an exact scorer for long prefill: on an R9700 a 131K-token prompt reads 8.7% faster, 230K 16%, 500K 79%; answers identical.

我们正是 262K 长上下文用户。但**只在 R9700（gfx12）上量过**，是否 gfx12 专用需读 0.1.45 源码判定（本地无树）->  **列为待核，不作承诺**。

### 3.4 反向更新我们自己的结论：`--parallel` / W9

0.1.45 把并发槽的代价量化了（逐字）：

> On a card that does not hold every expert the slots take VRAM from the expert cache: **a request alone runs 4-11% slower, and next to one request at a time WITH the draft layer, N together are only 1.0-1.15x faster**.

->  我们 `W9` / `P97` 判"不发车"**结论不变**，但**理由升级**：从"我们的 `vram_free 574` 放不下"升级为"**上游已量化：能加，但单用户先损失 4-11%，N 并发只有 1.0-1.15x**"。这条比原判更硬。

---

## 4 我方提交的现状（2026-10-20 实读）

| 条目 | 状态 | 关闭时刻 | 备注 |
|---|---|---|---|
| PR **#1855**（bench MI50 262k） | **closed（未合入）** | 10-19T16:56Z | 需要 `[Benchmark]` 前缀 + 在新引擎上复跑 |
| PR **#1877**（Monitor FRU 容量一致性） | **closed（未合入）** | 10-19T16:57Z | 需要 `[GUI]`（或 `[Engine]`）前缀 + 模板 + `/reopen` |
| issue **#1923**（缓存淘汰策略） | closed `not_planned` | 10-19T15:18Z | 我们已自撤动机，不救 |
| issue **#1926**（4 条文档级 note） | closed `not_planned` | 10-19T15:18Z | 第 4 条（`--dump-logits` 产出 0 字节）**10-16 被第三方 Boundlessmolson 在 Metal 上独立复现** => 该发现是真的 |

**关键事实**：`#1877` 的修复**没有**被上游自行收进 0.1.45 / 0.2.0（两版 release note 均无 FRU / `product_name` 相关条目）。生产 `/metrics` 实读仍是：

```
hardware_static.gpu_name = "Radeon Instinct MI50 32GB"     # FRU 原串是 ...16GB
hardware.gpu_mem_total   = 34,342,961,152 B (31.98 GiB)
hardware.gpu_pcie_gen=3 / width=16 / own_gen=4 / path=4/4
```

->  这个修复**只存在于我们的本地覆写 `serve-telemetry.py.patched`** 里。**升版必须重放 `apply_telemetry_pcie.sh`** 这条纪律，现在不只是"否则 PCIe 瓦片空"，而是"**否则 FRU 显示也退回 16GB**"。

---

## 5 建议

| 序 | 建议 | 理由 | 成本 |
|---|---|---|---|
| **1** | **不升 0.2.0-beta** | 无 gfx906 资产；vision 默认抢 1.47 GB（我们只剩 574 MiB）；Docker 镜像未发布 | 0 |
| **2** | **0.1.45 列为下一候选，但不急** | 唯一实质项是 #1896（我们已用 B7 绕过）+ 待核的 AMD 长上下文内核；仍需自建 gfx906 镜像 | 中 |
| **3** | **救 PR #1877**（建议做） | 改动只 **+16/-1、纯 Python**；上游确实没有这个修复；走 4 步 reopen 即可。标题改 `[GUI]`，补模板，`/reopen` | 低 |
| **4** | **暂不救 PR #1855** | 需要 **0.2.0-beta 引擎实跑**，而我们没有 gfx906 构建；等真上 0.1.45/0.2.0 再以 `[Benchmark]` 重提 | - |
| **5** | **#1923 不救、#1926 记录在案** | 前者我们已自撤动机；后者上游清场，但其第 4 条已被第三方复现，等升版时以新 issue 链接 | 0 |
| **6** | **纪律加硬** | `apply_telemetry_pcie.sh` 覆写现在是 FRU 修复的**唯一承载**，升版必须重放 | 0 |

**若你只说"按建议做"**，我会先做 **3**（rebase #1877 到 `main`、改标题、填模板、`/reopen` —— 这是唯一"花两分钟就可能拿回一条已修好的上游贡献"的动作），其余保持不动。

---

## 6 落盘物

`deploy/tmp/_rel_v0_1_45.md` · `deploy/tmp/_rel_v0_2_0-beta.md`（两版 release note 全文）· 本件。
