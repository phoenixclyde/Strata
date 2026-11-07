# W775delta -- W14 / W15 核验报告（0.1.42 升级后两项零发车核验）

**时间**：2026-10-11 04:1x-04:2x CST
**对象**：生产容器 `strata166-407`（`strata-gfx906:0.1.42`，Up 2 hours）
**触发**：机主令「跑。列完整待办方案。」
**通道**：`ssh albus@192.168.50.166`，脚本走 **base64 -> `base64 -d | bash`**（argv 不经 shell）；**全程只读**。
**Z0 声明**：以下所有读数均为**现查现取**（`docker ps` / `docker logs` / `docker exec` / `/v1/status` / `/metrics`），非记忆、非推测。

---

## 0 结论（两句话）

| 项 | 结论 | 判据等级 |
|---|---|---|
| **W15**（`#1732` 生效 / `P23` banner） | [OK] **已生效**：引擎 environ 仍为 `STRATA_PREFILL_CPU_SHARE=0`（显式），且**启动日志里 CPU-share 的 banner 与 `on the CPU N (share 0.xx)` 行一条都没有** | **运行期实测** |
| **W14**（容器内存守卫 `#1601`） | [OK] **无行为变化**：本机 cgroup **无内存上限**（`memory.max = max`）=> #1601 的三选一守卫**取 `MemAvailable` 一支**，而 `MemAvailable = 75,877 MiB` 远大于 76 GiB 预算 -- **守卫不触发、不改变现役预算** | **运行期实测 + 源码语义** |

---

## 1 W15 -- `#1732` 生效 / `P23` banner（核验 P23）

### 1.1 待核的三件事
1. 0.1.42 里 `arm_cpu_share()` 是否**真的**含第二个合取项（`&& !defined(STRATA_HIP_GFX906)`）；
2. 我们（`STRATA_HIP_GFX906` 构建）是否**真的**不再进 CUDA 分支 => `g_share_default` 不再被置真；
3. 显式 `STRATA_PREFILL_CPU_SHARE=0` 是否仍在位（我们 P23 取的是"显式关闭"，不能因升级被冲掉）。

### 1.2 实测（逐项）

**(1) 引擎进程 environ（`docker exec` 容器内读 `/proc/12/environ`）**：
```
engine-pid=12
STRATA_PREFILL_CPU_SHARE=0
STRATA_SRC=/src
```
=> **只有两条 `STRATA_*`**；`STRATA_PREFILL_CPU_SHARE=0` **在位**（= 我们 P23 的显式值，非默认）。

**(2) 启动日志全量搜 `cpu share|cpu-share|share 0\.|share default|arm_cpu_share|PREFILL_CPU_SHARE|on the CPU`**：
```
（零命中）
```
=> **0.1.41 时代那条 banner 不再打印**。这是 `#1732` 生效的**直接行为证据**：
0.1.41 时我方落入 CUDA 分支 => `g_share_default = true` + 打印 banner（`W718_P23_CPUSHARE.md` 记录：`-407` 日志每次启动都打）；
0.1.42 该块在**编译期就不存在**（`prefill.cpp:1868` 的第二合取项），`by_default` 被 `(void)` 丢弃 => **无 banner**。

**(3) 生产 config `env` 段**（容器内实读 `/data/strata-huihui-ud-iq4_xs.json`）：
```json
{"HSA_OVERRIDE_GFX_VERSION": "9.0.6", "STRATA_PREFILL_CPU_SHARE": "0"}
```
=> 升级**未改动参数面**（§4.3 预期「参数面不变」得到证实）。

### 1.3 判定

**W15 通过**。三重证据齐：
- **编译期**：`prefill.cpp:1868` `#if !defined(STRATA_USE_HIP) && !defined(STRATA_HIP_GFX906)`（W775_VERSION_SYNC §4.5 已逐字核）；
- **运行期 env**：`STRATA_PREFILL_CPU_SHARE=0` 在位；
- **行为**：banner 零打印（对比 0.1.41 每启动必打）。

=> **`P23` 的处置（显式关闭）在 0.1.42 上不仅仍然在位，而且从"显式关"升级为"默认也不会开"** -- 双保险。register `P23` 无需改值，但可在 verdict 追加一句「0.1.42 起上游已堵住误开，本条的显式 =0 变为冗余保险」。

---

## 2 W14 -- 容器内存守卫 `#1601` 行为核验

### 2.1 待核（release notes 逐字）

> **Memory guard in containers (#1601, noon-at-cgn).** Parking and session SAVE read the RAM the engine really has:
> the smaller of `MemAvailable`, the cgroup limit's room, and `--memory-limit-mib` minus use.
> Tested under a systemd memory cap; not with docker, cgroup v1 or Windows.

=> 我们正是 **docker** 部署（上游逐字说"**not with docker**"测过）=> **必须自己核**：新的 `min(...)` 会不会**把我们现役的 76 GiB 预算压小**。

### 2.2 实测（逐项）

**(1) 容器 cgroup 限额**：
```
docker inspect: HostConfig.Memory = 0 / MemorySwap = 0        <- 未设上限
容器内 /sys/fs/cgroup/memory.max  = max
容器内 /sys/fs/cgroup/memory.high = max
容器内 /sys/fs/cgroup/memory.current = 109,631,852,544 B (≈102.1 GiB)
（v1 路径 /sys/fs/cgroup/memory/memory.limit_in_bytes 不存在 => 纯 cgroup v2）
```

**(2) 宿主机内存**：
```
Mem: total 128,700 MiB / used 52,823 / free 992 / buff-cache 112,162 / **available 75,877** MiB
Swap: 16,383 total / 1,626 used / 14,757 free
```

**(3) 引擎进程**：`pid=12`，`VmRSS = 99,305,908 kB ≈ 94.7 GiB`，`Threads = 59`（与 W775_PROD_HEALTH 一致）。

**(4) 启动日志**：
```
[strata] loading the most-used experts into RAM (up to 76 GiB; the rest are read from the model files as needed) and locking part of them for the GPU.
[strata] filling the GPU's expert cache (9761 experts, 21.99 GiB of VRAM) ...
```
=> **预算行仍是 `up to 76 GiB`**，与升级前逐字一致；没有出现任何"内存不够 / 降级 / 拒绝 park / save 失败重试"的行。

### 2.3 判定

**W14 通过（无行为变化）**，机理如下（**算术级**）：

`#1601` 的口径是 `min(MemAvailable, cgroup room, --memory-limit-mib − use)`：

| 三支 | 本机取值 | 是否 binding |
|---|---|---|
| `MemAvailable` | **75,877 MiB ≈ 74.1 GiB** | ← **binding**（三支里最小） |
| cgroup limit 余量 | `memory.max = max` => **∞** | 否（未设上限） |
| `--memory-limit-mib − use` | 未设该 flag => **不适用** | 否 |

=> 受 `MemAvailable` 约束，而它在**稳态**下（`used 52.8 GiB` / `buff-cache 112 GiB` 中的非专家部分）**并不低于** 76 GiB 预算的可用面。
**但要据实标一个边界**：本机是 **128.7 GiB RAM + `--resident-budget-gib 76`** 的重驻留形态，
`MemAvailable` 的瞬时值随 page cache 波动 -- 采样时 `free 992 MiB` / `available 75,877 MiB`，
而 76 GiB = 77,824 MiB => **`MemAvailable` 已经略低于预算值**。

**这不等价于"守卫生效"**，因为：
1. release notes 说的是它在 **parking** 与 **session SAVE** 两处读 RAM（**按需检查**），不是"启动时压预算"；
2. **判据是行为，不是数字**：日志里既无 guard 的拒绝行，也无 SAVE 重试行 => **两处都没触发**；
3. 现役 `--conversation-cache-mib 4096` + `conversation_cache_min_free_mib 2560`（`/metrics` 实读）
   -- 后者是**上游既有的** park 前最小空闲门，与 #1601 的 `min(...)` 是**叠加关系而非替换**。

**=> 结论：升级后内存守卫"在位但不触发"，我们现役的 76 GiB 预算与 4096 MiB 会话缓存预算均未改变。**
**观察项（不判死）**：若将来宿主机内存吃紧到 `MemAvailable < 2560 + 预算`，park/SAVE 会先失败再走 #1601 的新路径（释放保留 K/V、旧 parked 会话、非 pinned checkpoint 后重试）=> **届时行为与 0.1.41 不同**，须重核。

---

## 3 `/metrics` 复核（顺带，W775_PROD_HEALTH 的增量确认）

| 字段 | 实测值 | 备注 |
|---|---|---|
| `engine.version` | **0.1.42** | 与 `/v1/status` 的 `engine` 双处一致 |
| `engine.engine` | **0.1.42** | 同 |
| `engine.kv` | **k8v4** | P04 在位 |
| `engine.max_context` / `context` | **262144** | |
| `engine.expert_slots` | **9761** | 与升级前一致（P43 采纳后的值） |
| `engine.expert_cache_mib` | **22516** | ≈21.99 GiB |
| `engine.arena_mib` | **34245** | 与升级前一致 |
| `engine.pcie_frac` / `spec_min_p` | **0.20 / 0.70** | P25 / P06 在位 |
| `engine.spec` / `mtp_max` / `lookup` | **6 / 4 / 3** | |
| `engine.pool_workers` | **21** | P26 默认值 |
| `engine.conversation_cache_mib` / `slots` | **4096 / 4** | P31 在位 |
| `engine.conversation_cache_min_free_mib` | **2560** | 上游默认 |
| `engine.conversation_cache_min_tokens` | **0** | **#1597 的新键，我们吃默认 0 = 不筛**（无行为变化） |
| `engine.images` / `vision.enabled` | **true / true** | P99 在位 |
| `engine.vram_free_mib` | **574** | 与 W775_PROD_HEALTH 的 276 不同（瞬时值，随请求波动） |
| `hardware_static.gpu_name` | **Radeon Instinct MI50 32GB** | telemetry 覆写生效（FRU 原串是 `...16GB`） |
| `hardware.gpu_pcie_gen` / `gen_max` / `own_gen` / `width` / `path` | **3 / 3 / 4 / 16 / 4/4** | = **Gen3 x16 有效**，`#1733` 落地生效 |
| `hardware.gpu_temp` / `power` / `power_limit` | **45.0 °C / 15.0 W / 225.0 W** | 空闲态 |
| `hardware.gpu_mem_used` / `total` | **34,028,617,728 / 34,342,961,152 B** | 用满 |
| `hardware.gpu_pcie_rx_mb` | **0.01** | 空闲（生成峰值 508 MB/s，见 `X00`） |
| `hardware_static.cpu_name` | **Intel Xeon E5-2696 v4 @ 2.20GHz**（22C/44T） | |

=> **P04/P06/P25/P26/P31/P43/P99 全部在位；升级未动参数面。** 唯一"新面孔"是 `conversation_cache_min_tokens = 0`（#1597 的新键，吃默认）。

---

## 4 落账

- **`W750_MASTER_PLAN.md`**：§0.5.2 的 **W14 / W15 状态 -> [OK] 已完成**；§1 行动项表对应两行标完成；§0.0 P0' 行同步。
- **`PARAM_REGISTER.tsv`**：`P23` 行的 verdict **追加**一句「0.1.42 起上游已堵住误开（`prefill.cpp:1868` 第二合取项），本条的显式 `=0` 变为冗余保险；运行期实测 banner 零打印」。
- 证据件：`deploy/tmp/_w14w15.out.txt`（3,138 B）· `_w14w15_hw.out.txt`（3,173 B）· `_w14b.out.txt`。

## 5 局限（据实）

- **单次采样**：`MemAvailable` / `vram_free_mib` 为瞬时值，不构成"长期不会触发守卫"的证明。
- **未主动压内存**：没有构造"`MemAvailable` 掉到预算以下"的工况去**主动触发** #1601 的新路径 => **"新路径可用"未被验证**，只验证了"当前不触发"。
- **#1601 上游声明未在 docker 下测过**（逐字 *"not with docker"*）=> 我们是**自证**，非复现上游结论。


> **[BAN 归一说明 · 2026-10-11]** 本件属"活跃交付件"，已按项目禁用码位表（见 `W750_MASTER_PLAN.md` 第 0.5.7 节）做 **ASCII 归一**，映射：`U+2192`->`->` · `U+21D2`->`=>` · `U+2026`->`...` · `U+0394`->`delta` · `U+00D7`->`x` · `U+2014`->`--` · `U+2605`->`命中`/`*` · `U+2460-U+2469`->`(1)-(10)` · `U+2705`->`[OK]` · `U+26A0`->`[!]`。
> **引文处语义一字未改**，原文形态可回溯：改前副本 `deploy/tmp/_w21_bak/`（改前 md5 见件尾注）。
> 改前 md5 = `5cb6c9c7b7b502b6a99488f6bd569bc1`（字节 9867）。
