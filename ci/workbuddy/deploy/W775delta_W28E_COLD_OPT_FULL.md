# W775delta W28E ---- 冷路径优化方案（**完整版**）

> 时间：2026-10-11 16:5x　机主令：「先审计记录 + 复核复活项有没有漏考，**先把方案做全了**」
> 承接：`W775delta_W28C_THREETIER_MECHANISM.md`（机制）· `W775delta_W28D_OPT_PLAN.md`（首版方案）

## 0 审计结论（先答"有没有记下 / 有没有漏考"）

**记录面：无缺口。** `todo_reconcile.py --strict` = **GAP=0**；今日日志 22 段齐全（W24 / W28 / W28C / W28D / W28D§8 均在）。

**全面性：有 5 组缺口（含我说错的一条）** —— 见 §1。本件把它们补全，**替代** `W28D` 成为正式方案。

---

## 1 复核发现的 5 组缺口

| # | 缺口 | 严重度 | 说明 |
|---|---|---|---|
| **G1** | **我说"prompt 期没有命中率口径"是错的** | **高** | `DETAILS.md:232` 逐字：`STRATA_IO_STATS=1`（**或 prefetch on**）*"adds the **page-cache hit / miss split (mincore)** and the **read-ahead used / unused counts**"* ⇒ **prompt 期的页缓存命中/未命中是可测的**。另有 `STRATA_LOOKAHEAD_STATS=1`（把预测与实际 miss 对账）。 |
| **G2** | **P54 的真杠杆是它的子键 `STRATA_IO_PF_STAGE`，我从未登记** | **高** | `DETAILS.md:229-243`：`STRATA_IO_PREFETCH=1` 单独在三条车道上实测 **-3.4% / -1.8% / -0.7%（≈0）** ⇒ **这解释了 W773 的"预取 0 次、无收益"**；而 **`STRATA_IO_PF_STAGE=1` 在**上游 RTX 3060 32GB** 车道（IQ3_XXS）实测 +25.7%**（**非本机 ---- AUDIT4 更正对象错置**）（另两条 -32.6% / -19%）⇒ **高方差，必须本机 A/B**。 |
| **G3** | **`STRATA_FS_SLOTS`（Foresight swap space）被我误判为"未激活"** | 中 | `DETAILS.md:1650-1651` + `foresight_swap.hpp:2`：**它是可开启的**（"opt-in: `STRATA_FS_SLOTS` > 0"）---- N 个**每层 VRAM 槽**，用"刚 miss 的 + 下一层 router 预测的"专家在 copy stream 上回填。我此前只写"`FS_AHEAD` 未激活"，**等于把整个机制排除在外**。 |
| **G4** | **resident 模式在 ROCm 上的形态没考虑** | 中 | `expert_source.hpp:543-544` 逐字：*"`pin = false` is ordinary pageable memory（**the ROCm arm: large pinned allocations can fail there, and it is what the HIP measurements used**）"* ⇒ **上游的 HIP 测量用的是 pageable**，而我们日志是 `mapped **pinned**`。关联 `TROUBLESHOOTING.md:102`：*"The budget is pinned (locked) in RAM, which leaves the OS and **the CPU workers** little room"* ---- **我们的症状正是 CPU workers 满载**。另有 `STRATA_EXCHANGE_ROTATE=1`（少 host 拷贝）与 `--adapt-async 1`（swap 移出关键路径）。 |
| **G5** | **没有写出上游定义的成功判据** | 中 | `DETAILS.md:187-188` 逐字：*"The server log shows, per request, how many expert reads went to the file（`resident RAM: ... blob reads from the file`: **0 in steady use**）"* ⇒ **判据 = `blob reads from the file` 稳态为 0**。我们现在是 **158 / 503 / ... / 24,720**。 |

---

## 2 成功判据（上游给的，直接可用）

| 判据 | 目标 | 我们现状 |
|---|---|---|
| **`resident RAM: <X> GiB of experts in RAM, <N> exchanged with the VRAM tier, <M> blob reads from the file`** | **M = 0（steady use）** | **M 达 24,720** |
| `file tier I/O this request: the OS read X MB from storage (F major faults) for Y MB` | X/F -> 0 | 单请求最高 **64,649 MB**（X）/ **222,659**（F）---- **[AUDIT5-A1 补遗] 两值属不同请求（`L2834` / `L2842`）** |
| 请求级 `prompt N tokens = R reused + K read in MS ms` | 冷请求 `read_ms` 显著下降 | 冷中位 **12.6 s** / 最大 **252 s** |

---

## 3 三条机制（回顾）+ **新补第四/第五条**

| 机制 | 内容 | 治它的项 |
|---|---|---|
| **M1** borrow/refill 无借区 | `--resident-budget-gib` **设计性关闭借区**（`expert_source.hpp:550-552`）⇒ 借走的 1,554 槽（3.49 GiB）每次从文件补回 | **OPT-A** |
| **M2** GPU 缓存那 22.0 GiB 无 RAM 副本 | 补集只装非 GPU 专家；GPU 缓存的专家**每次填充/重填都读文件** | OPT-A（借区覆盖尾部） |
| **M3** stager 用 RAM 档读真磁盘 | 4 线程 / ring 16 vs 上游同条件 **29 s vs 71 s** | **OPT-E（`STRATA_STAGER_SSD=1`）** |
| **M4（新）** 文件层读是**页故障**驱动 | 上游 `IO_PREFETCH` 族：预测+whole-blob pread+**staging** | **OPT-G（`STRATA_IO_PF_STAGE=1`）** |
| **M5（新）** pinned 副本挤 CPU workers | `TROUBLESHOOTING.md:102` | **OPT-H（`STRATA_RESIDENT_PIN=0`）** |

---

## 4 **完整杠杆清单**（含此前未登记的全部键）

### 4.1 一级杠杆（直接打冷路径）

| ID | 键 / 值 | 机制 | 上游实测 | 代价 | 优先级 |
|---|---|---|---|---|---|
| **OPT-A** | `--resident-experts`（去 `--resident-budget-gib`）+ `STRATA_RESIDENT_HEADROOM_GIB=0.5` | 启用**借区** ⇒ 借出的槽的专家留 RAM | `DETAILS.md:167` *"so a prompt reads nothing from the SSD either"* | RAM −3.5 GiB | **1** |
| **OPT-G** | **`STRATA_IO_PF_STAGE=1`**（配 `STRATA_IO_PREFETCH=1`） | 每个未缓存专家**staged 进缓冲并让该层等** ⇒ 大并发读 | **+25.7%**（32 GB 车道）/ -32.6% / -19% | 高方差；须本机 A/B | **2** |
| **OPT-E** | **`STRATA_STAGER_SSD=1`**（或 `STAGER_THREADS=32`+`STAGER_RING=128`） | prompt 路 staging 并行度 **4→32 线程 / ring 16→128** | **29 s vs 71 s（4K chunk，上游 RTX 5070/NVMe 平台）** | 页缓存真温时 4-7× 慢 | **3** |
| **OPT-B** | `--no-prefill-borrow` | 不借槽 ⇒ 无 refill | `INTEL.md:248/333` | prompt 缓冲自占 VRAM 3.49 GiB | 4 |
| **OPT-F** | `STRATA_IO_PREFETCH=1`（**单独**） | whole-blob preads + 预测层线程 | **-3.4/-1.8/-0.7%（≈0）** | 低 | 5（作 OPT-G 的前置） |

### 4.2 二级杠杆（副作用/条件性）

| ID | 键 / 值 | 机制 | 备注 |
|---|---|---|---|
| **OPT-H** | `STRATA_RESIDENT_PIN=0` | 补集改 **pageable**（上游 HIP 测量的形态）⇒ 不挤 CPU workers | `DETAILS.md:185` 逐字 *"gives the mapped mode's exact tokens"* ⇒ **不改答案** |
| **OPT-I** | `STRATA_EXCHANGE_ROTATE=1` | adaptive swap 交所有权而非拷贝 ⇒ 少 host 拷贝 | `DETAILS.md:180-182`；**同 tokens** |
| **OPT-J** | `--adapt-async 1` | swap 移出关键路径（helper 线程） | `DETAILS.md:170-179`；**非 bit-exact from run to run**（须记） |
| **OPT-K** | **`STRATA_FS_SLOTS=N`**（+`STRATA_FS_BUDGET`） | Foresight：**每层 N 个 VRAM 槽**存"刚 miss + 预测"的专家 | VRAM −N×48 槽；`DETAILS.md:1650` |
| **OPT-C** | `--prefill <chunk>` 固定小值 | 借区 ∝ chunk ⇒ 借区变小更易进 RAM | 需先验"借区 ∝ chunk"成立 |
| **OPT-D** | 启动前 `drop_caches` / 先起引擎 | 抬高引擎测得的 `available` | 只影响启动那一刻 |
| **OPT-L** | `STRATA_PIN_RESERVE_GIB` | pin 阶段的保底量（默认=RESIDENT_HEADROOM） | 与 OPT-A 同族但**独立键** |
| **OPT-M** | `STRATA_LOOKAHEAD_K` / `STRATA_IO_PREFETCH_DEPTH`(默认 2) / `STRATA_IO_PF_THREADS`(默认 8) / `STRATA_IO_PF_AHEAD` | 预测宽度/深度/线程/是否 demand-only | 与 OPT-F/G 同族 |
| **OPT-N** | `STRATA_READ_AHEAD=0` / `STRATA_FILL_AHEAD=N` | 启动填充的 readahead / 预读对数（默认 256） | 启动期 |
| ~~划掉~~ | `--resident-budget-gib` 调大 · `STRATA_UNBUFFERED_LOAD=1` | 前者设计上无借区；后者上游 `#773` 腰斩 | — |

### 4.3 **度量杠杆**（回答"命中率"，G1）

| 键 | 给什么 |
|---|---|
| **`STRATA_IO_STATS=1`** | **页缓存 hit / miss 拆分（mincore）+ read-ahead used / unused** ⇒ **prompt 期命中率** |
| `STRATA_LOOKAHEAD_STATS=1` | 预测 vs 实际"GPU 缓存外的路由"对账 ⇒ prompt 期 miss 结构 |
| `STRATA_IO_PF_STAGE=1` 时附带的统计 | 见上 |

---

## 5 测量协议（替代 decode `ms/step`）

**三态**：**C 冷**（唯一前缀，`reused=0`）/ **W 温**（重复前缀）/ **D decode 稳态**（保留，仅描述 decode）。

**每请求同时记**：
1. `prompt N tokens = R reused + K read in MS ms`（wall 分解）
2. `file tier I/O this request: the OS read X MB (F major faults) for Y MB`
3. **`resident RAM: ... M blob reads from the file`** ⇒ **主判据（目标 0）**
4. 启动行：`allocating %.2f GiB cache complement`（**AUDIT4 修正**：该值随 boot 浮动 ---- 同一 `--resident-budget-gib 76` 下实测有 **33.44 / 33.45 / 36.80 GiB** 三值，故「> 33.44」**不能**单独判「借区进了 RAM」；**更干净的二元硬证** = `FileExpertSource: N of M of the prompt path lendable slots keep their experts in RAM too` 的 **N == M**（仅 `lend=true` 时打印，见 `expert_source.cpp:3105-3109`））· `the prompt path borrows N slots` · `stager takes the RAM profile`
5. **并行系统遥测**：`amdgpu.gpu_utilization` / `system.cpu{user,system,iowait}` / `disk.sda`
6. **报告 p50 / p90 / max**（禁只报均值）
7. **两侧都开 `STRATA_IO_STATS=1`** ⇒ 页缓存 hit/miss 拆分（**回答命中率**）

**车纪律**：单变量（**同路径不可组合**，W723）· ABBA 交错 · 每块丢 r0 热机项 · 页缓存状态在两侧对称（必要时两臂都先 `drop_caches`）· `flock` + `trap restore EXIT`。

---

## 6 车序列（按期望值 × 成本排序）

| 序 | 车 | 变量 | 判据 | 备注 |
|---|---|---|---|---|
| **1** | **B8** | `STRATA_STAGER_SSD=1` | `read_ms` C/W + 遥测 | 单变量；**非零风险**（页缓存真温时该档 **4-7x 慢**，见 §4.1 OPT-E 代价；**AUDIT4 更正**）---- 治 M3 |
| **2** | **B7** | `--resident-experts` + `STRATA_RESIDENT_HEADROOM_GIB=0.5` | **`allocating` > 33.44 GiB**（硬证）+ `blob reads from the file` → 0 | 治 M1/M2 |
| **3** | **B9** | `STRATA_IO_PREFETCH=1` + `STRATA_IO_PF_STAGE=1` | `read_ms` + `IO_STATS` | 治 M4；**高方差，必测** |
| **4** | **B10** | `STRATA_RESIDENT_PIN=0` | CPU 占用 + `read_ms` + parity | 治 M5；**须 parity 门** |

> 前两车跑完即可判定"覆盖（M1/M2）"与"并行度（M3）"各占多少；`IO_PF_STAGE` 与 `RESIDENT_PIN` 是第二轮。

---

## 7 复现命令

```bash
L=/home/albus/strata166/data/strata-huihui-ud-iq4_xs.log
grep -a 'blob reads from the file' $L | tail -5          # 主判据（目标 0）
grep -a 'allocating .* cache complement' $L | tail -3    # 借区硬证
grep -a 'stager takes the' $L | sort | uniq -c           # stager 档
grep -a 'file tier I/O this request' $L | tail -5
curl -s 'http://127.0.0.1:19999/api/v1/data?chart=disk.sda&after=-3600&points=120'
```


## 8 车序现况更新（2026-10-11 17:5x ---- B7 已固化上线）

> [!] `B7` 已固化（register `P66`/`P65` -> ADOPTED、`P09` -> REJECTED），且**生产实测 `blob reads from the file = 0`**（上游成功判据达成，见 `W775delta_W4X_RES_RESULT.md` §8）。
> => **`B9`（`IO_PREFETCH` + `IO_PF_STAGE`）的靶（file 层读）已消失 ⇒ B9 作废**（若将来 file 层读重新出现再测）。
> => **`B10`（`RESIDENT_PIN=0`）仍为候选**（它的靶是 CPU-worker 的内存压力 / pageable 形态，与 file 层读无关）。
> => 新增一轮：**B7-long**（长 prompt 受控 A/B，量化长冷请求下的收益；harness `deploy/tmp/_w4z_rc.sh`）。
