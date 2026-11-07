# W775delta W28 ---- 冷路径重新定线（W26/P54/#1670 的定向错误）

> 时间：2026-10-11 16:2x　触发：机主实测反证 ---- 一个请求进来，**GPU 不动、CPU 长时间满载、硬盘读负载拉满**
> 结论：**此前的测量线有方向性错误**。不是"参数没测全"，是**测错了阶段**（测 decode 稳态，而机主感知的是 prompt 冷读）。

---

## 0 一句话

我此前把一句**范围语句**（`resident RAM mode ... (no file reads)`，讲的是 adaptive swap 路径）**外推成了全局结论**，并据此得出「file tier 非瓶颈」「专家大多已驻留」「命中率 95-98%」。**全部对冷请求不成立**：
- 冷请求 **0 复用**，`read_ms` 中位 **12.6 s**、p90 **38.6 s**、最大 **252 s**；
- 文件层累计读 **371 GB（真存储）/ 1.10 TB（专家合计）**，单请求最大 **79.7 GB**，major fault **单请求 max 222,659**（**198 请求中 84 次非零**；AUDIT4 防误读：非累计）；
- 同期系统侧：**GPU 利用率 p50 = 0**、磁盘读峰值 **356 MB/s**、CPU 全核 **51%**。

---

## 1 反证（四层，全部现取）

### 1.1 请求级：冷 vs 温（产线日志 196 条 prompt 行）

| 组 | n | prompt_tokens (med) | read_ms (med / p90 / max) | prompt tok/s (med) |
|---|---:|---:|---|---:|
| **冷（`reused=0`）** | **76** | 5,217 | **12,564 / 38,590 / 251,925** | 402.9 |
| 温（`reused>0`） | 120 | 14,301 | 2,045 / 13,448 / 46,144 | 93.2 |

冷请求**按长度分档**（`read_ms` 中位）：

| prompt tokens | n | read_ms med | read_ms max | prompt tok/s med |
|---|---:|---:|---:|---:|
| 0 - 200 | 19 | 1,857 | 2,460 | **48.1** |
| 200 - 2,000 | 11 | 3,656 | 5,321 | 119.6 |
| 2,000 - 20,000 | 40 | **20,734** | 44,974 | 455.1 |
| 20,000 - 60,000 | 4 | 76,282 | 114,169 | 465.6 |
| >= 60,000 | 2 | **248,162** | 251,925 | 353.7 |

原始行逐字：
```
strata serve: prompt 110793 tokens = 0 reused + 110793 read in 244400 ms (453.3 tok/s)
strata serve: prompt  64026 tokens = 0 reused +  64026 read in 251925 ms (254.1 tok/s)
strata serve: prompt  13296 tokens = 0 reused +  13296 read in  30396 ms (437.4 tok/s)
```
**注意**：连 **60 token 的小请求**（冷）也要 **1,994 ms** ---- 说明冷态有**固定代价**（不只是 prompt 长度）。

### 1.2 文件层：`file tier I/O this request`（198 条）

| 指标 | med | max | sum |
|---|---:|---:|---:|
| OS 从存储读 | 40.5 MB | **64,649 MB** | **371,808 MB（371 GB）** |
| 专家读合计 | 1,766.7 MB | **79,756 MB** | **1,099,239 MB（1.10 TB）** |
| major faults | 0（84/198 非零） | **222,659** | -- |

=> **真存储读占专家读的 33.8%（371.8 / 1,099.2）**，与上游文档 *"the third of them outside the RAM budget"* 吻合。
> **[AUDIT5-A1 补遗 2026-10-11 19:xx]** 上表 `max` 列的 **64,649 MB / 79,756 MB / 222,659** 分属**三条不同请求**（`L2834` / `L2569` / `L2842`）；**原文下方「逐字行」曾把三者拼成一行（非逐字）**，已按日志拆回三行。累计值 `371,808 / 1,099,239` 与各 `max` 本身此前已由 AUDIT4 §4.4 复核成立。

逐字行：
```
strata serve: file tier I/O this request: the OS read 64649.1 MB from storage (1406 major faults) for 23613.1 MB of expert reads   <- `L2834`（60-token 首请求）
strata serve: file tier I/O this request: the OS read 27429.5 MB from storage (222659 major faults) for 38258.9 MB of expert reads   <- `L2842`（64,026-token 请求）
strata serve: file tier I/O this request: the OS read 3375.7 MB from storage (0 major faults) for 79756.2 MB of expert reads   <- `L2569`（110,793-token 请求）
FileExpertSource: RAM budget 76.00 GiB: 14819 of the 33.45 GiB of experts the GPU cache does not hold, by profile rank; the rest are read from the files
strata generate: the file tier reads through the file cache (re-checked with the RAM copy built (33.45 GiB): 82.8 GiB available, 0.0 GiB of it still to be taken by the RAM copy, 22.0 GiB of experts read from the files: the file cache can keep the ones that come back)
strata serve: resident RAM: 33.45 GiB of experts in RAM, 3501 exchanged with the VRAM tier, 158 blob reads from the file
```

### 1.3 系统层：netdata 48h（`amdgpu` + `system.cpu` + `disk.sda`）

| 指标 | min | p50 | p90 | max |
|---|---:|---:|---:|---:|
| `amdgpu.gpu_utilization` (%) | 0.00 | **0.00** | 64.09 | 99.97 |
| `system.cpu` user (全核 %) | 0.62 | 0.65 | 6.76 | **51.46** |
| `system.cpu` iowait (%) | 0.00 | 0.00 | 0.77 | **20.78** |
| `disk.sda` reads (KiB/s) | 0.00 | 54.59 | 7,584.3 | **356,205.5** |
| `disk_ops.sda` reads (ops/s) | 0.00 | 1.65 | 354.2 | **3,857.5** |

**66 / 1440 采样点**满足「GPU <= 2 且（CPU 忙 >= 30 或 iowait >= 5 或 读 ops >= 50）」。代表点：

| 时刻 | GPU% | CPU(user+sys)% | iowait% | disk reads (KiB/s) | read ops/s |
|---|---:|---:|---:|---:|---:|
| 10-11 13:36 | 0.31 | 4.4 | **20.78** | **356,205** | 1,022 |
| 10-11 02:50 | **0.00** | **51.1** | 0.00 | 0.3 | 0.0 |
| 10-11 02:52 | **0.00** | **50.9** | 0.00 | 59.7 | 1.8 |
| 10-11 02:54 | **0.00** | **51.1** | 0.00 | 4.6 | 0.1 |
| 10-11 02:22 | 0.00 | 2.7 | 1.86 | 286,899 | 1,364 |
| 10-11 11:30 | 0.85 | 2.1 | 2.69 | 298,479 | 597 |

**两条独立源互证**：引擎说那条 **110,793-token 冷请求**（`L2569`，`read 244,400 ms`）自己的 `file tier` = **OS 从存储读 3,375.7 MB**、专家读 **79,756.2 MB**；**[AUDIT5-A1 补遗]** 此前把 `64,649 MB` 归给它（实为**另一条 60-token 首请求** `L2829/L2834` 的 max），`222,659 major faults` 又属**第三条** 64,026-token 请求（`L2842`）。

### 1.4 源码层（0.1.42，`deploy/tmp/src142/`）

三层存储是**设计如此**（不是异常）：

| 层 | 容量（本机） | 逐字依据 |
|---|---|---|
| GPU cache（VRAM 槽） | **9,761** | `resident RAM mode: ..., 9761 in the GPU cache` |
| RAM 补集（page-locked） | **33.45 GiB**（14,819 专家） | `RAM budget 76.00 GiB: 14819 of the 33.45 GiB ... by profile rank` |
| **文件层** | **22.0 GiB** | `22.0 GiB of experts read from the files` |

- `docs/DETAILS.md:247-249`：`--resident-budget-gib N` = *"the resident variant for a model whose experts do not all [fit]... **the rest are read from the files**"*
- `docs/UNSLOTH_Q4.md:175` 逐字：*"**Reading a prompt streams every expert once per 4K chunk**, and the third of them outside the RAM budget [come from the SSD]"*
- `docs/TROUBLESHOOTING.md:105`（已知问题）：*"Decode got slower in 0.1.40 on a 32 GB PC with `--resident-budget-gib N`, and **the drive is read hard** (#1194, #1116, #1085)"*

---

## 2 错在哪（逐条，含我自己的）

| # | 我曾写的 | 实际 | 错型 |
|---|---|---|---|
| E1 | 「miss 走 RAM 交换、**no file reads**」（W26） | 那句是 **adaptive swap 路径**的范围语句；**prompt 冷读**走文件层 | **范围语句外推**（与 §8 坑6「banner 单向证据」同型） |
| E2 | 「生产命中率 **95-98%**」（W26/#1923 更正） | 那是 **`decode expert cache hit rate`**（decode 口径）；prompt 阶段冷请求 **`reused=0`** | **口径错配** |
| E3 | 「**file tier 非瓶颈**」+ 0.5-1.2 GB/s vs 15.75 GB/s 约 7%（**P54** + **我贴给 #1670 的回复**） | 冷路径真存储读 **371 GB**、单请求 79.7 GB、222,659 major faults、磁盘 356 MB/s | **结论错误**（对冷路径） |
| E4 | 「专家大多已驻留」 | GPU cache 只 9,761 槽；RAM 补集 33.45 GiB；**文件层 22.0 GiB** | **结论错误** |
| E5 | 车测主口径 = **decode `ms/step`** | 机主感知的是 **prompt `read_ms`**（12.6 s ~ 252 s） | **测错阶段**（测了用户不感知的那个） |

---

## 3 正确的模型：三层存储 x 两态请求

```
                 ┌────────────────────────────────────────────────┐
  冷请求(C)      │  每 chunk 把每层 routed expert 过一次         │
  reused = 0     │    命中 GPU cache (9,761)  -> 最快            │
  read_ms 12.6s  │    命中 RAM 补集 (33.45 GiB) -> PCIe 搬       │
  ~252s          │    未命中 -> 文件层 (22.0 GiB) -> SSD/页缓存  │  <-- 你看到的
                 └────────────────────────────────────────────────┘
  温请求(W)      前缀命中 -> 只读新增部分（med 224 tok / 2.0 s）
  reused > 0
```
- 冷态**固定代价**也在（60-token 冷请求 = 1.99 s）。
- 文件层的"真存储 vs 页缓存"取决于**页缓存是否还留着**（`the file cache can keep the ones that come back`）。

---

## 4 重定的测量线（W28）

**主口径从「decode `ms/step`」改为「请求级 wall time，并分态」**：

| 口径 | 定义 | 说明 |
|---|---|---|
| **C 冷**（新主口径之一） | `reused == 0` 的请求 | 用**唯一前缀**强制冷 |
| **W 温**（新主口径之一） | `reused > 0` | 前缀命中的真实体验 |
| D decode 稳态 | 现口径 | **降级为「只描述 decode 阶段」**，不再代表端到端 |

**每次请求必须同时采**：
1. 引擎行 `prompt N tokens = R reused + K read in MS ms`（wall 分解）
2. 引擎行 `file tier I/O this request: OS read X MB (F major faults) for Y MB of expert reads`（I/O 归因）
3. **系统遥测并行**：GPU util · CPU(user/sys/iowait) · disk read MB/s 与 ops/s
4. 报告 **p50 / p90 / max**（禁只报均值；`p90 = 3x p50` 正是被均值抹掉的东西）

**自变量**：prompt 长度分档 · 冷/温 · `--resident-budget-gib`（RAM 补集大小，直接决定文件层占比）。

---

## 5 受影响的既有结论（需重开 / 加限定）

| 条目 | 处置 |
|---|---|
| **`P54`**（`STRATA_IO_PREFETCH` 无收益） | **加限定**：该结论基于"文件层非瓶颈"的前提，**冷路径下前提不成立** => 重开复核 |
| **`W26`**（缓存 = 预填 + `adapt()` 迁移，0.9564） | **加限定**：成立范围仅 **decode 稳态**；**不覆盖 prompt 冷读** |
| **`#1670` 回帖**（我发的，"the file tier is not our bottleneck"） | **需更正**：该断言被冷路径数据反证。草稿见 §7（**未发**） |
| **`W13`/`#1923` 头部空间** | 命中率口径进一步限定到 **decode**；其"本机价值下调"结论方向不受影响（生产 decode 仍 95-98%） |
| **「`--prefill` 上限 8192 已撞顶」**（W17b 结论） | 需复核：段落是按"每 4K chunk 重读"算的，chunk 越大重读越少 => 撞顶方向仍对，但**收益量级**要重估 |
| 各车（W12D/W4x/§4 族） | **不推翻**（它们测的是 decode，且结论是"无增益"） ---- 但**它们全都漏了冷路径**，故"不采纳"的范围要写明 |

---

## 6 可能有效的旋钮（**待验证**，不要照抄）

| 旋钮 | 机理 | 预期 |
|---|---|---|
| `--resident-budget-gib N`（现 76，实际补集只 33.45 GiB） | 补集越大 -> 文件层 22.0 GiB 越小 | **可能是最大杠杆**（需实测：N 与冷 read_ms 的关系） |
| `--mmap-experts` | 改页锁为 mmap，让文件缓存接管 | 上游文档已知"stall"风险，需实测 |
| `--expert-cache auto` / `--vram-reserve-mib` | VRAM 槽数 -> 第一层命中 | 已知边际 |
| `routing-aware prefetch` / `STRATA_LOOKAHEAD` | 提前拉下一层 | 日志显示已在跑（39 次 prefetch on） |
| `--prefill` chunk | 每 chunk 重读一次全层专家 | 已撞 8192 上限 |
| `STRATA_PREFILL_CPU_SHARE` | CPU 侧算 | 我们 = 0 |

---

## 7 待机主过目的上游更正草稿（`#1670`，**未发**）

> 要点：我们 2026-10-11 在 `#1670` 说 "the file tier is not our bottleneck"。**该断言被我们自己的冷路径数据反证**（详见 §1）。更正稿待定稿后再发 —— **不抢先发半成品**。

---

## 8 复现命令

```bash
# 请求级
grep -a 'strata serve: prompt [0-9]' /home/albus/strata166/data/strata-huihui-ud-iq4_xs.log
# 文件层归因
grep -a 'file tier I/O this request' /home/albus/strata166/data/strata-huihui-ud-iq4_xs.log
grep -a 'FileExpertSource:' /home/albus/strata166/data/strata-huihui-ud-iq4_xs.log
# 系统侧（netdata）
curl -s 'http://127.0.0.1:19999/api/v1/data?chart=amdgpu.gpu_utilization_unknown_AMD_GPU_card0&after=-172800&points=1440'
curl -s 'http://127.0.0.1:19999/api/v1/data?chart=disk.sda&after=-172800&points=1440'
curl -s 'http://127.0.0.1:19999/api/v1/data?chart=system.cpu&after=-172800&points=1440'
```

产物：`deploy/tmp/_cold_raw.txt`（原始行）· `deploy/tmp/_netdata_48h.txt`（48h 曲线）· `deploy/tmp/_cold_parse.py` · `deploy/tmp/_netdata_an.py`
