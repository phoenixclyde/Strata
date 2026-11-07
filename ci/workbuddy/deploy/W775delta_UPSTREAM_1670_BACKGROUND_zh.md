# `#1670` 事项说明（中文）---- 我们发了什么、哪里错了、这次要发什么

> 用途：给机主过目用。配套英文送审稿 = `deploy/W775delta_UPSTREAM_1670_FOLLOWUP.md`（**已作废，未发**）。
> **[!] 结局（2026-10-11 19:4x）**：机主令**不再跟进、删除我们全部评论** => 3 条（`6083995120` / `6106913235` / `6107050493`）已 DELETE（204/404），issue 现仅剩他人 2 条；**未发新内容**（删除即最彻底的撤回）。快照 `deploy/tmp/_1670_deleted_snapshot.json`。

## 1 这个 issue 是什么

- **上游仓库**：`Niko1221/Strata`
- **issue `#1670`**：「**[Feature]: Layer-major prefill for streamed experts**」---- 一个**特性提案**。
- **提出者/实现者**：`vizdatom`，分支 `vizdatom/Strata@perf-ryzen`（base = 0.1.39 + 10 commits），
  新增 6 个开关（`STRATA_PREFILL_LAYER_MAJOR` / `STRATA_PREFILL_LM_TOKENS` / `STRATA_LM_PREFETCH` /
  `STRATA_PREFILL_DIRECT` / `STRATA_BIN_WARM` / `STRATA_PREFILL_WARM`）与两个新 kernel。
- **它想解决什么**：流式专家（`--mmap-experts`）下，prompt 每个 chunk 都要把**所有层**的专家从文件层重读一遍；
  layer-major 改按"层"主序取用，减少重读。**在 6 GB 卡上收益明显**。
- **适用条件（vizdatom 逐字）**：*"Layer-major only applies with **streamed experts** on a single GPU and
  prompts of two or more chunks."*

## 2 我们为什么会掺进去

2026-10-09 我们看到这个提案，觉得"值得给一个不同形态机器的数据点"，于是贴了第一条评论
（`6083995120`），核心是：**我们这台 MI50 上提示读取不是 PCIe 瓶颈**，所以 layer-major 的收益在我们这儿可能兑不出来。
08:20 `CC-David-CC` 催 vizdatom 放分支，08:40 vizdatom 放了分支与 env 清单，15:29 我们贴了数据点。

## 3 我们的三条评论（逐条事实核）

### (1) `6083995120`（2026-10-09T15:29:40Z，642 B）---- 数据点

内容两点：

| 说法 | 出处 | 事实核 |
|---|---|---|
| `1.83 distinct experts per layer` | `W718_P23_CPUSHARE.md:51`（实测表格「PCIe 专家 \| 1.83 distinct/layer」） | **有出处** [OK] |
| `~15.75 GB/s link`（Gen3 x16 有效带宽） | `W728_PCIE_TELEMETRY.md:282/334` + `W736_PR_CANDIDATES.md:145` | **有出处** [OK] |
| `0.5-1.2 GB/s` 实测流量（约 7%） | `W728_PCIE_TELEMETRY.md:334`（逐字「实测流量 0.5-1.2 GB/s，远未打满 Gen3」） | **有出处** [OK] |
| **「the file tier is not the bottleneck」** | 由上面三个数字**推论**得出 | **错**（对冷路径）[X] |

**错在哪**：那三个数字测的是**PCIe 链路占用**（温缓存/稳态下的专家搬运），而"文件层是否瓶颈"要看
**真存储读**。我们自己的实测（2026-10-11 W28 线）证明：**冷请求的真存储读是 371 GB，占专家读 1.10 TB 的
33.8%**；单请求最高 79.7 GB；`222,659` 次 major fault；netdata 48h 里有 **66/1440** 个"GPU 闲但 CPU/磁盘忙"的点。
=> **推论跨度太大**（PCIe 不忙 ≠ 文件层不忙）。
> 我们**在自己的账上**已把它记为错误：`W775delta_W28_COLD_PATH_REDESIGN.md:110` 的 **E3 = 「结论错误」（对冷路径）**。

### (2) `6106913235`（2026-10-11T07:59:32Z，1,173 B）---- reply

内容三点：(a) layer-major 在本机**不激活**（我们是 resident 专家，无 `--mmap-experts`/`--stream-experts`）；
(b) 给出当时的实际配置与日志行；(c) 因此**不移植**到 HIP/gfx906。

| 说法 | 事实核 |
|---|---|
| 「不激活」（resident 模式） | **对** [OK]（`W775delta_W24_1670_LAYER_MAJOR.md` §1.3：生产 args 逐字无 `--mmap-experts`） |
| 「resident RAM mode: 33.44 GiB in RAM, 9761 in the GPU cache」 | **对** [OK]（当时日志） |
| 「不移植」 | **对** [OK]（移植含新 kernel + 10 commits，代价高、本机又不激活） |
| **「The earlier data point also applies to the streamed case ... a large reduction in re-reads would buy much less here」** | **错**（这是在**复述 (1) 里那句已被推翻的推论**）[X] |

### (3) `6107050493`（2026-10-11T08:17:28Z，2,022 B）---- correction

内容：**主动撤回** 10-09 那条的结论（"our own logs contradict that"），并给出支撑数据。

| 说法 | 事实核 |
|---|---|
| 撤回 10-09 的结论 | **对** [OK]（有 W28 数据支撑） |
| 累计 198 请求：`371,808 MB` 存储读 / `1,099,239 MB` 专家读（约 34%） | **对** [OK]（AUDIT4 §4.4 复核） |
| 冷请求 `76 of 196`、中位 `12.6 s`、p90 `38.6 s`、max `252 s` | **对** [OK] |
| netdata：`GPU 0%` / CPU 约 `51%` / 磁盘峰 `356 MB/s` | **对** [OK] |
| layer-major 仍不激活（resident 而非 mmap） | **对** [OK] |
| **`(a single request: 64,649 MB from storage, 79,756 MB of expert reads, 222,659 major faults)`** | **错** [X]（见 §4） |

## 4 我们的问题（两处，都是这次审计才查出来的）

### 问题一：correction 里那个括注把**三条不同请求**写成了**同一条**

生产日志逐字（`deploy/tmp/_audit5_ev/strata-huihui-ud-iq4_xs.log`）：

```
L2834  the OS read 64649.1 MB from storage (1406 major faults) for 23613.1 MB of expert reads   <- 一条 60-token 首请求
L2842  the OS read 27429.5 MB from storage (222659 major faults) for 38258.9 MB of expert reads <- 一条 64,026-token 请求
L2569  该请求自己的 file tier = the OS read 3375.7 MB (0 major faults) for 79756.2 MB           <- 一条 110,793-token 请求
```

=> `64,649.1`（存储读的**单请求最大**）、`79,756.2`（专家读的**单请求最大**）、`222,659`（major fault 的
**单请求最大**）是**三个 max，来自三条请求**；原括注把它们并列成 "a single request"。
**累计值（371,808 / 1,099,239 / 34%）不受影响，是对的。**

### 问题二：07:59 的 reply 复述了被撤回的结论，而 correction 只点了 10-09 那条

correction 开头逐字 *"Correction to our comment of **2026-10-09** on this issue."* ---- 没提 07:59 那条。
于是 issue 上留下"一个已被撤回的结论还挂在另一条评论里"的尾巴。

## 5 这次要发的 follow-up 起什么作用

**作用 = 把我们在这个 issue 上的三条发言收敛到与事实一致**，具体两件事：

1. **更正括注**：把三条请求的三个 max 拆开，并声明累计值不受影响；
2. **一并撤回 07:59 那句复述**（correction 当时没覆盖它）。

**不动的**：**「layer-major 在本机不激活」这个结论**（resident 而非 `--mmap-experts`）---- 它**不受这两处影响**，
且已被 `W775delta_W24_1670_LAYER_MAJOR.md` 逐条核过。所以 follow-up 不会改变我们对 layer-major 的立场，
只是把**关于文件层的那句话**彻底说清、把错误收干净。

## 6 中文版正文（对照英文送审稿）

> 英文送审稿见 `deploy/W775delta_UPSTREAM_1670_FOLLOWUP.md` §1。中文对照如下（**只供机主阅读，不发出**）：

> **对这个 issue 上我们评论的两处更正。**
>
> **一、** 在我们 2026-10-11T08:17Z 的更正里，我们写了：
> `(a single request: 64,649 MB from storage, 79,756 MB of expert reads, 222,659 major faults)`。
> 这三个数是**三条不同请求**各自的单请求最大值，不是同一条：
> 　- 一条 **60 token** 冷请求：从存储读 **64,649.1 MB**（1,406 major faults）
> 　- 一条 **64,026 token** 冷请求：从存储读 **27,429.5 MB**（222,659 major faults）
> 　- 一条 **110,793 token** 冷请求：从存储读 **3,375.7 MB**（0 major faults）
> 该评论里的**累计值不受影响**：198 条请求里文件层从存储读了 **371,808 MB**、对应专家读 **1,099,239 MB**（约 34%）。
>
> **二、** 我们 2026-10-11T07:59Z 的回复里重复了 2026-10-09 那个说法
> （"早期的数据点对**流式**场景同样成立……大幅减少重读在我们这里买不到多少"）。**那句也一并撤回。**
> 我们的更正当时只点了 10-09 那条，但 07:59 回复里的同一句同样错：**在冷路径上，文件层就是瓶颈**
> （1,099,239 MB 专家读里有 371,808 MB 来自真存储）。
>
> 两处更正**都不触及**我们的另一个结论，它仍然成立：**layer-major 在我们的配置下不激活**，
> 因为我们跑的是 residency（RAM 驻留）专家，而不是 `--mmap-experts`。
