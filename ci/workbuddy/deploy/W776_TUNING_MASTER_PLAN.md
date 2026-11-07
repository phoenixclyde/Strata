# W776 生产调优总方案（0.2.2b / 引擎 0.1.47）

> **已冻结（2026-10-31 17:4x）。方案权威改为 `deploy/W832_OPT_PLAN_V2.md`（§0.0）。**
> 下面那句"以 `W786_TARGET_CORRECTION.md` 为唯一入口"**已失效**（W786 → W829 → W832 是四代转手，收口后只有一份）。

> **[2026-10-25 04:5x 排期与目标双重收口] 执行排期以 `W786_TARGET_CORRECTION.md` 为唯一入口（R1-R8）。**
> 两层作废：(a) 本文 §5（C 批）、§9（D 批）、§10（E 批）、§11（F 批）、`W785` 的 Q1-Q9 五套编号已互相覆盖，全部转为历史留档；
> (b) **本文的优化目标（decode 提速）本身选错了**——decode 只占端到端墙钟的 0.5-43%，prefill 占 57-99.5%（W786 §1）。
> 另外 §P87 上限表已废（基线含 `--resident-experts`，且分项和差 15%），新三档基线见 W786 §2.1。
> 正文的现状描述、机制解释、否决复核、测量协议仍有效。

> 生成 2026-10-22 02:1x · 机主令「我要全面的调优方案」·**02:2x 已按 register 全表复核修正（v2）**
> 口径：每条断言都带出处（实测日志行 / `--help` 原文 / 源码行号 / register ID）。推算值一律标 **[推算]**。
> 生产容器 `strata166-407`，镜像 `strata-gfx906:0.2.2b`，`/metrics` 已实读。

---

## 0 结论先行（含 v1 的自我纠错）

**v1 我写了 12 条杠杆，拿 register 全表一核，其中 5 条是已经实测否决过的（详见 §3）。下面是剔掉重复项之后的真实结论。**

1. **瓶颈不在 SSD、不在内存、不在 PCIe。** 实测 `the OS read 22.2 MB from storage (1 major faults) for 23613.1 MB of expert reads; page cache held 63269.5 MB` —— 专家读取 23.6 GiB 里只有 22 MB 来自磁盘；`Swap used 0`、`pgsteal_file 0`。
2. **瓶颈是一个结构性比例**：`prefill plan inputs: 55.4 GiB experts, 22.0 GiB in the GPU caches, 36.9 GiB RAM copy ... PCIe 12.0 GB/s`。**VRAM 只装得下 39.7% 的专家**（9761 / 24576 个 blob），其余 60.3% 由 20 个 CPU worker 在 AVX-2 上算（`this CPU has no AVX-512`）。
3. **[2026-10-25 04:5x 修正] 预填不是「GPU 空转」。** 原文写「预填 = CPU-bound（GPU 空转）」，依据是 netdata 在 2026-10-22 那次 105K 请求上报的 `GPU 0%`。用 `rocm-smi --showuse` 每 1 s 直读复核（M 档热态，49 样本）：`100 x42 / 99 x4 / 98 x1 / 68 x1 / 0 x1`，中位 100、零值 2% => **预填期间 GPU 与 CPU 同时满载**，是纯算力 bound（日志同时证 `file tier 0.0 GiB` 即磁盘 0 读、`PCIe 12.0 GB/s` 未饱和）。**这条修正的直接后果**：`--prefill-pipe`（重叠 I/O）与 `STRATA_PREFILL_CPU_SHARE`（借 idle CPU 池）两个方向的前提都不成立，已从队列移除（W786 §4.2）。两段的墙钟占比也需改写：prefill 占 57%（S 2.8K）/ 90%（M 21.8K）/ 99.5%（L 99K），见 W786 §1。
4. **[纠错] PLE 不是大头。** v1 我按 `34102 rows/s` + 每 token 16 行推算出"PLE 占预填 22.5%"，并建议 `--ple-io ram`。**register `P91` 已实测该开关 -45%，上游社区实测"the same as default"** => 推算方向对但结论错，已列为否决项（§3-1）。
5. **[2026-10-25 04:5x 作废] 显存侧那 3.35 GiB 拿不到。** 原文按源码注释算出「可腾 1487 槽（+15.2%）」，但 `--kv-grow` 的门要求 `vmm_available()`，而 `src/core/vmm.cpp:158/167` 把 HIP VMM 限定在 `!defined(STRATA_HIP_GFX906)`，`:299-303` 恒返回 false（同处注释逐字点名 gfx906）。三臂实测（含去 `--resident-experts`）`expert_slots` 恒为 9901、引擎日志打出 `--kv-grow is off`。=> P32 的 214 MiB 算术确实错（816 B/cell 是每层），但结论更强：**不是收益小，是根本不可达**。
6. **[回归] pool worker 从 21 掉到 20。** 0.1.42 臂日志 `21 pool workers`，0.1.47 臂 `20 pool workers on 1..20`，core 21 空着；而 register `P26` 的 calibrate 实测是 **"21(=引擎默认) 最优"**（36.0 vs 14=34.8 vs 10=34.2 vs 5=29.1）=> 升版把最优默认丢了，应显式写回 21。
7. **真正没测过的空白只有 6 个旋钮**：`--ple-inflight`、`--pool-tasks`、`--host-core`、`--aux-cpus`、governor、`--spec-min-p --calibrate`。全部在 register 里查无记录。
8. **一个实测事实而不是猜想**：`conversation_cache: requests_reused 0 / reused_tokens 0 / parked 2` —— 4 GiB 会话缓存预算一次都没复用上，这是多轮对话体感差的直接原因。**[2026-10-25 04:5x] 这条是本方案里最早、也最被忽视的一条**：从 W776 到 W785 五个版本都把它排在队列末尾或判成「外部问题」，直到 W786 实测出「修复后 M 档第二轮 44 s -> 0.5 s」（88 倍）才升为第一。教训：**已经在手的实测事实，优先级不该低于新挖的机理**。

---

## 1 现状基线（全部实读，非记忆）

### 1.1 运行期 `/metrics`

| 项 | 值 |
|---|---|
| version / kv | `0.1.47` · `k8v4` |
| context / prefill_cap | `262144` · `8192`（`prefill_stages 1`、`prefill_pipe 0`） |
| expert_slots / cache | `9761` · `22516 MiB`（每槽 2.307 MiB） |
| vram_free | **574 MiB** |
| arena_mib | `37819` |
| pool_workers | **20** |
| spec / mtp_max / lookup | `6 / 4 / 3`（`--spec 4` 被 suffix-draft 改写的既有账实不符） |
| pcie_frac / spec_min_p | `0.20` / `0.70` |
| conversation_cache | `4096 MiB / 4 slots`，`parked 2`，**`requests_reused 0`** |
| gpu_pcie | `gen3 / own_gen4 / width16 / path 4/4` |
| gpu_power / limit | `15.0 W` / `225 W`（idle） |

### 1.2 启动段关键行（`strata-huihui-ud-iq4_xs.log` 19658-19722）

```
profile /src/data/expert-profile.bin: 24576 ranked pairs, built for 24576 slots
expert cache auto: 22.89 GiB free, 700 MiB reserved (+218 MiB for the draft head) -> 6782 slots
expert cache 9761 slots, 21.99 GiB of VRAM
prefill plan inputs: 55.4 GiB experts, 22.0 GiB in the GPU caches, 36.9 GiB RAM copy
  (1554 lend slots kept), file tier 0.0 GiB; 78.7 GiB available for the page cache;
  PCIe 12.0 GB/s; drive 0.45 GB/s (... SATA-class SSD ...); a 32768-token prompt
prompt chunk auto: 8192 tokens, a 96-slot ring
the prompt path borrows 1554 CUDA0 cache slots (3.49 GiB)
20 pool workers on logical processors 1..20, the host thread on 0 (draining too)
aux cpus: threads ... go to CPUs 22,21,43 (off at start; a request's aux_cpus=1 turns it on)
PLE direct read probe: 34102 rows/s (fine)
PLE on, table 320001536 rows of ...-00002-of-00003.gguf      <- 3.2e8 行 x 90 B = 26.8 GB
mtp: draft layer loaded, 1089 MiB of VRAM (experts 675, dense 111)
574 MiB of VRAM free with everything loaded
resident RAM mode: 36.93 GiB of experts in RAM (page-locked), 9761 in the GPU cache
this CPU has no AVX-512: the expert kernels run on AVX-2
```

### 1.3 单请求实测（20,438 token 冷读）

```
reading the prompt: 20,433 of 20,438 tokens, 42 s so far
done: 1 tokens in 43 s (20.6 tok/s), expert cache 85.6% hit
=> /metrics: prompt_ms 42693.2 / prompt_read 20438 => 2.089 ms/token = 479 tok/s
   冷态还带 decode waited 5601.1 ms in 9762 fetches
```

### 1.4 主机资源

| 项 | 值 | 判读 |
|---|---|---|
| RAM | 125.7 GiB total / available **80.5 GiB** / Cached 114.0 GiB | 够 |
| Shmem | **40.15 GiB**（= resident 36.93 GiB 的 page-locked 副本） | 专家在 RAM 存两份：pinned 副本 + GGUF page cache(63 GB) |
| Swap | 16 GiB，**已用 0** | 从未换出 |
| CPU | 22 core / 44 thread / 单 NUMA / L3 55 MiB | 单节点，无 NUMA 调优空间 |
| governor | **`schedutil`（intel_cpufreq）** | 可改 performance |
| THP / HugePages | `madvise` / **0** | 专家 arena 是 mlock，THP 基本无关 |
| SSD | `sda` Fanxiang S100Pro，**mq-deadline**，0.45 GB/s | 只在冷启动相关 |
| 容器 ulimit -l | `unlimited` | 对齐上游配方 |

---

## 2 瓶颈分解（机理，不是猜）

### 2.1 预填 2.089 ms/token 的构成

| 成分 | 判断 | 依据 |
|---|---|---|
| CPU 专家（60.3% 的行，20 核 AVX-2） | **主导**，GPU 被它拖住 | 预填期 GPU use 实测 0%；`no AVX-512` |
| GPU 专家 + attention + dense | 被 CPU 段掩盖 | 同上 |
| 专家交换 / PCIe | 小 | `pcie_share 0.0`、`files 0 blobs` |
| PLE 16 行 direct 读 | 0.469 ms 是**探测值**，不是实际占用 | 实操中与专家读并行，`--ple-io ram` 反而 -45% |

**结论**：预填时 GPU 在等 CPU。所以"给 GPU 更快的 kernel"没用，"给 CPU 更少的活 / 更好的调度"才有用。

### 2.2 显存已经榨干（再分配的四个抽屉）

| 抽屉 | 量 | 依据 |
|---|---|---|
| expert cache | 21.99 GiB | `9761 slots`，每槽 2.307 MiB |
| K/V（全 262144 cell） | **3.35 GiB** | `generate.cpp:7735` "the K/V of a 262K context (3.35 GiB with the drafter's at int8)" |
| MTP drafter | 1.09 GiB | `mtp: draft layer loaded, 1089 MiB` |
| dense + head + 窗口 | 余量 | `arena_mib 37819`（虚拟 arena，非实际） |

**专家总数已实读**：`native_experts.txt` 头行 `n_expert 512, total 59519795200` = **55.4 GiB / 48 层 x 512 = 24576 个 blob**（与 `24576 ranked pairs, built for 24576 slots` 逐字对上）。

=> 想把 55.4 GiB 全塞进 VRAM 需要 22.0 -> 55.4 GiB，物理上不可能。任何承诺"全部进显存"的方案都是错的。
=> 但 decode 命中率实测 87-97%、预填 85.6%，**远高于** 39.7% 的专家数占比 => adaptive tier 的热度排序有效，**天花板在总容量，不在算法**。

---

## 3 已否决复核表（v1 的 5 条撞车，逐条给 register 原文）

> 这一节是本方案的主体之一：**省掉重跑已经跑过的车**。register 88 行已全表扫过。

| # | v1 我的建议 | register | 历史实测 | 本轮处置 |
|---|---|---|---|---|
| 1 | L1 `--ple-io ram`（我估 +15~25%） | **P91 REJECTED** | 「技能 §7.7 实测 **-45%**」；上游 `2026-10-01-community-2x-titan-rtx` 原文 "`--ple-io ram` measured **the same** as the default `direct`" | **维持否决**。两方证据都不支持，且我方是负收益 |
| 2 | L2 `--pool-workers 21`（我估 +3%） | **P26 REJECTED** | `calibrate 实测：21(=引擎默认)=36.0 / 14=34.8 / 10=34.2 / 5=29.1 => 默认最优，不改` | **改判**：不是"调参"，是**修 0.1.47 的默认漂移**（21 -> 20）。判据是回到 A 臂的 21，不是"比 21 更快" |
| 3 | L3 `--vram-reserve-mib 768` | **P62 REJECTED** | 「机制不匹配：AMD_HIP.md:199 用途是 keep more VRAM free than the default 700，场景是显卡还需驱动桌面；本机无头专卡 => 调高即减槽，边际」 | **重开**：0.1.47 新增运行期警告 `only 495 MiB free (below 512) ... the driver can page GPU memory to system RAM, decode falls to a few tok/s and a window may never finish (**#2065**)` —— 新版本、新 issue、证据等级高于旧文档口径 |
| 4 | L4 `--prefill auto:16384` | **P22 REJECTED** | `W709 交错 A/B（18,083-token 冷 prompt，各 2 轮）：预填 454.05 vs 455.05 = -0.22%（分辨力 1.2~1.4%）=> 无效果` | **维持否决**。我引用的 `+0.5..+5.8%` 是上游 RDNA4 的数字，本机已实测不复现 |
| 5 | L5 `--kv-grow`（我估 +15.2%） | **P32 REJECTED** | 「收益算账：`816 B/cell x 262144 = 214 MiB`；省下来也只多 **约 93 槽（+0.95%）**」 | **重开**：214 MiB 是**单层**。源码原文 3.35 GiB => **1487 槽（+15.2%）**。且 0.1.47 生效条件多一条 `!o.resident_cpu_experts`（`generate.cpp:5154`），我们开 `--resident-experts` 时它**从未真正生效过** |

另外三条 v1 提及但同样是旧账：`--prompt-cache-tail`（P21，温 TTFT 无差，与 `--prompt-cache-every 16384` 重复）、`--kv-resident`（P63）、`--no-pool`（P92）。

---

## 4 有效杠杆（剔重后 10 条，按 ROI 排序）

### T1 `--pool-workers 21`：修默认漂移（不是调参）

- **事实**：0.1.42 臂 `21 pool workers`；0.1.47 臂 `20 pool workers on 1..20`，core 21 空着（aux 才用它，aux 默认 off）。
- **依据**：P26 的 calibrate 已证明 21 优于 14/10/5；0.1.47 把默认降了 1。
- **判据**：`/metrics.pool_workers == 21`；预填中位数回到 A 臂水平；**不承诺额外增益**。
- **成本**：零，纯线程数（help "Moves threads only, never a result"）。

### T2 `--vram-reserve-mib 768`：引擎点名要的（#2065）

- **事实**：`WARNING: only 495 MiB of VRAM free at the start of this request (below 512 MiB) ... Add --vram-reserve-mib 768 to the config's args`。
- **代价**：68 MiB 缺口 -> 约 30 槽（-0.3%）。
- **判据**：`vram_free >= 700`；连续 5 次长请求无 `below 512 MiB` 警告；`expert_slots >= 9730`。
- **风险**：低。最坏是槽位少 30 个。

### T3 `--kv-grow`：唯一被算错的历史结论（上限 3.35 GiB）

- **门槛（`generate.cpp:5202-5209` 逐字，0.2.4.2；旧版为 5154 —— AUDIT6 P2-6 更正行号）**：`on = asked && !multi_gpu && o.kv_resident <= 0 && !o.expert_profile.empty() && !o.resident_cpu_experts && o.expert_cache != 0 && !remote && vmm_available() && o.batch == 0 && !o.vram_elastic && o.peer_device < 0`
- **障碍**：`--resident-experts` = `--mmap-experts --resident-cpu-experts`，直接把它关掉。要开必须先去掉 `--resident-experts`。
- **预期**：+1487 槽（+15.2%）=> 命中率 +2~4 pt => 预填 +2~4%、decode +1~3% [推算]。
- **副作用（正面）**：省下 36.93 GiB pinned 副本，`MemAvailable` 从 80.5 升到约 117 GiB。
- **副作用（负面）**：专家改为依赖 page cache（63 GB 已缓存，但可被回收）。**这是本项最大风险。**
- **判据**：启动出现 `elastic K/V: N of 262144 cells in VRAM (x.xx of 3.35 GiB)`；`expert_slots >= 11000`；S/M/L 三档都不退。
- **顺序**：**最后做**，因为它同时动 RAM/VRAM 两个面。

### T4 `--ple-inflight N`（register 查无记录）

- **机理**：`--ple-inflight N outstanding SSD reads (default 256)`；34.1K rows/s 是 256 并发下测的，4K 随机读的队列深度未见顶。
- **预期**：+0%~10%，零 RAM 成本，不占显存，不改答案。
- **判据**：>= +2% 才采纳；扫 256(默认)/512/1024。
- **注意**：**这是 PLE 方向唯一还开着的门**（ram 已废、prefill 已废）。

### T5 `--pool-tasks N`（register 查无记录）

- **机理**：help "Batched CPU expert tasks per GU/Down phase (0..4096). Default 0 = 3 per participating thread"。
- **判据**：扫 1/2/4/6/8；中位数 >= +3% 才采纳。这是 CPU 专家段的批处理粒度，**最贴近瓶颈的旋钮**。

### T6 `--host-core` / `--aux-cpus`（register 查无记录）

- **机理**：help "Windows sends a GPU's interrupts to one logical processor, usually the first ... a spinning host there waits for them"（Linux 同理，GPU 中断多在 cpu0）。我们 host 就在 0。
- **预期**：+1~3% [推算]。
- **判据**：看启动行 `pool workers` 与 `aux cpus` 实际落点；与 T1 分车（都动拓扑）。

### T7 governor `schedutil -> performance`（register 查无记录）

- **事实**：`intel_cpufreq` + `schedutil`，空载 `scaling MHz 47%`。预填是持续满核，升频滞后吃前几秒。
- **预期**：+0~2%；零成本，随时回。
- **判据**：预填首 chunk 的 tok/s；满载 `scaling_cur_freq` 稳定在 turbo。

### T8 会话缓存复用（`requests_reused = 0` 是实测缺陷）

- **事实**：`conversation_cache: budget 4096 MiB / slots 4 / parked 2 / requests 3 / requests_reused 0 / reused_tokens 0`。
- **方向**：`--conversation-cache-min-free-mib`（现 2560）、`--conversation-cache-min-tokens`（现 0）、`--prompt-cache-spread`（P33 相关，未被否决）。
- **判据**：连续两轮同会话，第二轮 `reused > 0` 且 `prompt_ms` 降 >= 50%。
- **价值**：单轮无变化，**多轮体感最大**。

### T9 `--spec-min-p --calibrate`（上游提供本机校准，我们没跑过）

- **事实**：help "`--spec-min-p P` ... (setup writes 0.5; `--calibrate` measures it on this PC)"；我们用的是 0.70。
- **判据**：calibrate 给出的值 vs 0.70，decode 中位数对比；必须同臂重复对照（§6.3）。

### T10 `--adapt-async`（P71 CANDIDATE，未关单）

- **依据**：P71 记 `expert_source.hpp:543` 上游 HIP 测量用的是 **pageable**，我们日志是 `mapped pinned`；`TROUBLESHOOTING.md:102` 明说 pinned 预算会让 **CPU workers** 没地方。
- **判据**：decode 中位数 >= +3%；预填不退。

---

## 5 执行计划

> 纪律：每批一个变量（拓扑类 T1/T6 互斥分车）；每车 `--prompt-cache 0` + nonce，`reused` 必须为 0。
> 全部改动走 `register -> gen_config.py --write -> 推 166 -> restart -> verify_config FAIL=0 -> /metrics`。

| 批 | 内容 | 车 | 窗口 | 为什么排这里 |
|---|---|---|---|---|
| **C1** | T1 `--pool-workers 21` + T2 `--vram-reserve-mib 768`（合成一车，判据正交） | 1 | 45 s 重启 + 5 min | 前者修回归、后者防 decode 崩，都零风险 |
| **C2** | 三档基线 S/M/L（**首次建 L 档 105K 基线**） | 1 | 15 min | 后面所有车都要跟它比 |
| **C3** | T5 `--pool-tasks` 扫描 1/2/4/6/8 | 5 | 25 min | 最贴近瓶颈的空白旋钮 |
| **C4** | T4 `--ple-inflight` 扫描 512/1024 | 2 | 12 min | 零成本探底 |
| **C5** | T6 `--host-core last` / `--aux-cpus auto` | 2 | 12 min | 拓扑类，与 C1 分开 |
| **C6** | T7 governor | 1 | 6 min | 系统项，不重启容器 |
| **C7** | T8 会话缓存复用 | 2 | 12 min | 独立面 |
| **C8** | T9 spec-min-p 校准 + T10 adapt-async | 2 | 15 min | decode 面 |
| **C9** | T3 `--kv-grow`（去 `--resident-experts`） | 2 | 25 min | 风险最高，最后 |
| **C10** | 合规基线（上游冻结 fixture / temp 1.0 / top_p 0.95 / effort xhigh / track=custom） | 1 | 25 min | 与社区可比的第一个数字 |
| **D0** | **源码级门禁**：rocprof/ISA 量 (a)`qsa_gate_apply` 占 decode 比例 (b)`warp_max/warp_sum` 的 DPP 形态与 lane 覆盖 (c)`expf` 在 softmax kernel 的指令数 | 1 | 20 min | 见 §9；**不发车就没有 D1-D4** |
| **D1** | T11 `warp_max/warp_sum` -> `v_add_f32_dpp` 融合（routeK 手法） | 1 | 改码 + 重编 ~25 min | 唯一"无精度风险"的源码级项 |
| **D2** | T12 `qsa_gate_apply` 的 fp64 sigmoid -> fp32 | 1 | 改码 + 重编 | 输出本来就是 fp16，fp64 是纯浪费 |
| **D3** | T13 softmax 的 `expf` -> `v_exp_f32` | 1 | 改码 + 重编 | 有精度代价，连 llama.cpp 都不用，最后做 |
| **D4** | T14 `readfirstlane` SGPR 广播 | 1 | 改码 + 重编 | 收益 <1% 就放弃 |

**C1 立即执行**（机主已令「弄」）；C2 紧随其后拿基线；C3 起按结果滚动推进。

---

## 6 测量协议

### 6.1 三档

| 档 | prompt tokens | 场景 |
|---|---|---|
| S | ~2.9K | 短问答（Open WebUI 常态） |
| M | ~23K | 中等上下文 |
| L | **~105K** | 长文档（今天问题的主场景，**从未单独建基线**） |

### 6.2 每车规则
- `--prompt-cache 0` + `--conversation-cache-mib 0` + 唯一 nonce => 必须 `reused = 0`、`read = ptok`，否则作废。
- 5 runs/档（拓扑类可 3 runs），报 median / min / max / n，分档不合并。
- decode 输出 >= 250 token，避免首 token 开销污染。
- 排除项必须列出：errors / cancellations / unexpected cache reuse / 缺测。

### 6.3 非确定性（硬约束）
已实测：同一 prompt 同一引擎连发 3 次，输出 620 / 610 / 634 token，**三种 md5**。
=> **答案 md5 不能作 identity 判据**；比答案必须先做同臂重复对照。比性能只看中位数。

---

## 7 不做（带出处）

| 方案 | 判定 | 理由 |
|---|---|---|
| `--ple-io ram` | 不做 | P91 -45%；上游 Titan 实测 "the same" |
| `--prefill auto:16384` | 不做 | P22 实测 -0.22%（分辨力 1.2-1.4%） |
| `--prompt-cache-tail` | 不做 | P21 温 TTFT 无差，与 `--prompt-cache-every 16384` 重复 |
| 换更小量化让专家全进 VRAM | 不做 | 需 55.4 -> <=22.0 GiB（-60%）= 2-bit 级，质量不可接受 |
| 加第二块 MI50（`--peer-device`） | 不做 | 硬件不在，且与 `--layer-split` 互斥 |
| `--batch N` 并发 | 暂不做 | `vram_free 574`；T3 后可重估 |
| 跟 llama.cpp master | 不做 | 实测编不过：`moe_mmq.cu` 3 处签名/窄化（104/159 失败） |
| `STRATA_ADAPT_OVERLAP_RESIDENT=1` | 不做 | 实测 -0.14%/-0.06% / +0.00%/+1.66%，全在噪声 |
| `--kv q4_0` 替 `k8v4` | 暂不做 | KV 总量仅 3.35 GiB，再省一半不值当动已验精度 |
| `--mmap-experts` 单开 | 不单开 | help 原文 "71.97 vs 34.78 ms/token cold vs warm" |

---

## 8 一句话

**这张单子真正的新东西只有三件：kv-grow 被少算了 16 倍（214 MiB -> 3.35 GiB）、pool worker 默认从 21 漂到 20、会话缓存实测一次都没复用上。其余七个旋钮是本机从没碰过的空白区；再剩下的，register 里已经跑过并否决了。**

---

## 9 gfx906 源码级移植（W782 并入，T11-T14）

> 底稿：`W782_GFX906_SRC_TRIAGE.md`（三方源码对照：routeK 的 gfx906 kernel / llama.cpp pin 3cf03257 / Strata 0.1.49.2）
> 与 §4 的 T1-T10 的区别：**T1-T10 全是改配置（重启几十秒）；T11-T14 要改 C++ 源码 + 重编镜像（25 min/车）**。所以它们排在全部配置类之后。

### 9.1 结论表

| 编号 | 机理 | 能移？ | 数值影响 | 位置 |
|---|---|---|---|---|
| **T11** | warp 归约用 **`v_add_f32_dpp` / `v_max_f32_dpp`** 把「shuffle + 加法」合成一条 | **能，干净** | **none**（加法顺序不变） | Strata `qsa.cu:428-436`；routeK `gfx906-common.cuh` |
| **T12** | `qsa_gate_apply` 用 **fp64 sigmoid**，结果却压 fp16 | 不是移植，是自己浪费 | 有（fp64->fp32） | `qsa.cu:519/799`；调用面 `layer.cpp:1298` / `verify.cpp:1902` / `mtp.cpp:1037` |
| **T13** | `v_exp_f32` 硬件指数替代 `expf` | 能，有代价 | **有**（exp 精度 2^-10） | `qsa.cu:486`；routeK `fast_exp_f32` |
| **T14** | `readfirstlane` SGPR 广播 | 能 | none | 全树未见 |
| — | LDS `ld+1` padding | **不用移** | — | Strata 已有（`dflash2.cu:107` 的 `[32*33]`） |
| — | `b128` LDS / `dwordx4` | **不用移** | — | Strata 已有（324 处 `__shared__`、362 处 `uint4/float4`） |
| — | MMQ 的 GCN tile 配置 | **同一份** | — | 同用 llama.cpp pin，`mmq.cuh:263 #ifdef GCN` |
| — | MoE GEMM 的 BM 分档 | **不可比** | — | Strata 的 GEMM 在 `s2_expert_grouped.cu`，无 `BM` 维度 |

### 9.2 D0 门禁（不发车就没有 D1-D4）

必须先用 rocprof/ISA 量出三件事，否则改了也不知道是不是它起作用：

1. `qsa_gate_apply_kernel`（fp64 那个）占 decode 墙钟的比例 —— 决定 T12 值不值
2. `warp_max/warp_sum` 编出来的实际形态（`v_mov_b32_dpp` 与 `v_add_f32` 是否各一条）**以及 lane 覆盖**：
   `qsa.cu:428` 的循环只到 `o=16`（覆盖 32 lane），而 gfx906 wave 是 64 宽 —— **这一条必须核实**，不能凭源码断言它错，也不能凭它"跑得好"就说它对
3. `expf` 在 softmax kernel 里的实际指令数 —— 决定 T13 上限

### 9.3 发车条件（逐条）

| 项 | 前置 | 判据 | 风险 |
|---|---|---|---|
| T11 | D0 显示归约占比 >1% 且 lane 覆盖有改进空间 | decode 中位数 >= +2%；同臂重复对照无系统性差异 | 低（数值不变） |
| T12 | D0 显示该 kernel >2% | decode >= +3%；fp16 输出在 ulp 级 | 中（fp64 可能是有意的数值稳定） |
| T13 | D0 显示 softmax >3% | decode >= +3%，且接受 top-1 变化（与 HC_Q8 同级） | 中高（改答案） |
| T14 | 前面都做完 | 收益 <1% 放弃 | 低 |

### 9.4 为什么 llama.cpp 一条都没用

全树 grep：`v_add_f32_dpp` / `v_exp_f32` / `__builtin_amdgcn_exp` **零命中**。它走通用 `__shfl_xor_sync` + `expf`。
两种解释：要么没试，要么试过不划算（softmax 不是它的瓶颈 / 精度门不过）。
**所以 T11/T13 不能因为"routeK 用了"就认为一定更快**——D0 的必要性就在这里。


---

## 10 W783 并入：FA 源码级结论 + 内核资源实测 + 校准结果（E0-E8）

> 底稿 `W783_GFX906_FA_DEEPDIVE.md`。§9 的 T11-T14 是"三方源码对照"的第一版，本章用**真下载的四棵树 + 166 上的 ELF 实测**把它重排，并以 E 批取代 D 批。
> 未变的两条：(a) 源码类改动一律 env 门控、默认关闭；(b) 编译与调试只在 166。

### 10.1 新证据改变了三个判断

| 旧判断 | 实测 | 影响 |
|---|---|---|
| "预填注意力可调 `launch_bounds(THREADS,3)`" | `prompt_attn_i8v3` 在 gfx906 二进制里 **grep=0**，TU 只有 6,256 B 无 fatbin | **该内核没编进去，调它无效**，T11/§9 里相关设想作废 |
| "溢出是 FA tile 的问题，occ 钉 1 可解" | 101/1646 内核溢出，但 decode 注意力 `attn_chunk` **priv=0**；真热点是 `qsa_select::block_topk` **1120 B** 与 `fused_gr::gr_down_v3` **956 B + 256 VGPR** | 溢出治理目标改为选择器与 GR，不是注意力 |
| "`--pcie-frac 0.20` 是历史值、该重校" | 校准器实测 0.36 仅 **+0.6%**（39.46 vs 39.23），0.55 起劣化 | **不必改**，0.20 维持 |

### 10.2 新增/改判的条目

| 编号 | 内容 | 机理与证据 | 判据 |
|---|---|---|---|
| **A1** | Q8 量化 Q + `dp4a` 做 KQ | routeK `fattn-q8.cuh:342-395/429`；我方 `qsa_decode_attn.cu:342` 的 q 是 fp32 | decode >= +2%，needle 6/6 |
| **A2** | 溢出治理（1120 B / 956 B 两处） | ELF 实测（W783 §6.1）；手法参考 `fattn-q8.cuh:608-618` 的 LDS 覆盖 | 各 >= +2%，parity 全过 |
| **A3** | `v_exp_f32` 替 `expf` | `qsa.cu:486` + `CMakeLists.txt:545` 无 fast-math；反证：llama.cpp 全树零使用 | decode >= +3% |
| **A5** | GQA 打包只限 decode | `launcher.cu:145` 逐字 `nc2 > 1 && seq_q > 2 -> nc2 = 1` | 作为约束记录，不实施 |
| **A6** | KV 切分 + 合并 | 我方 `decode_attn_i8_split_kernel` 已有 | 不实施 |
| **E5** | `native_mmvq` upstream 布局 | `native_mmvq.cu:1157` 的 `g_multi_exact=true` 从未计时，且**无 env 可翻** | 两向都测，无差异则维持 |
| **E7** | 路由 fp64 治理 | `router_top10.cu:220-226/258`；fast kernel 的替代实现存在但被 wave kernel 先返回挡掉（`:456-465`） | 需 parity 覆盖 |
| **E8** | `--pcie-frac 0.36` | 校准 +0.6% | 我方 M/L 档 >= +1% 才改 |

### 10.3 校准结果（`tools/calibrate.py`，166，rc=0，1292 s）

- `--spec-min-p **0.70**`：41.8 vs 0.5 的 39.1 => **比上游默认高 6%**；复核轮 41.7/42.2/39.5 vs 38.4/38.8/36.7 再次确认
- `--pool-workers`：20 最优（41.9/38.4），13/10/5 依次更差
- `--adapt-*`：**默认最优**（41.96/42.45），1/80/0.97 与 1/160/0.97 均更差
- `--pcie-frac`：0.36 仅 +0.6%，不采纳
- `STRATA_SH_STREAM=1`：校准器两次 +2.4%，**我方同口径复核 M 档 +0.25% / decode 0.00%，判噪声，已否决（P83）**

### 10.4 批次（取代 §5 的 D 批）

| 编号 | 内容 | 前置 | 预计 |
|---|---|---|---|
| E0 | rocprofv3 取 kernel 级占比 + 确认 `block_topk` 哪个变体在跑 | 无 | 20 min |
| E1 | ~~SH_STREAM 三档复核~~ | **已完成，否决** | - |
| E2 | A1 Q8 量化 Q + dp4a | E0 | 60 min |
| E3 | A2 溢出治理（两处） | E0 | 40 min |
| E4 | A3 `v_exp_f32` | E0 | 30 min |
| E5 | mmvq upstream 布局（加 env） | 无 | 35 min |
| E6 | DPP 融合归约 | E0 | 30 min |
| E7 | 路由 fp64 | E6 | 30 min |
| E8 | `--pcie-frac 0.36` 复核 | E1 | 20 min |

**E0 是唯一门禁**：没有 kernel 级占比，A1/A2/A3/E6 改了也不知道是不是它起作用。

---

## 11 W784 并入：全覆盖清点后的统一排期（取代 §10 的 E 批）

> 底稿 `W784_GFX906_FULL_SWEEP.md`。覆盖：routeK 202 个 gfx906 相关文件、45 个自有开关、13 份 DEVLOG（9,900 行）、llama.cpp pin 与 master 的 68 个差异文件。
> 本章的核心变化：**先用 E0 实测给每一项算价值上限，再排期**。§10 里的 A1/A3/E6 不是错，是上限太低（注意力一族合计只占 GPU 的 6.7%）。

### 11.1 E0 实测（M 档 21,827 token，97 窗口稳态）

`74.76 ms/window = verify 56.36 + commit/emit 0.05 + draft 7.04`，其中 GPU 55.65 ms（verify 期间 GPU 占用 98.7%）。

| 去向 | ms | 占比 |
|---|---|---|
| 专家流（VRAM hits 7.44 + waitB 6.49 + waitCPU 4.01） | **17.94** | **32.2%** |
| HC 投影（hc0/hc1 的 down+up） | **7.15** | **12.8%** |
| 量化 + dense GEMV（q8+qkv 3.92 + q+q-idx 2.18 + 0.15） | **6.25** | **11.2%** |
| router+plan+bell | 3.87 | 7.0% |
| 注意力一族（attention 2.11 + scores+topk 1.61） | 3.72 | 6.7% |
| 其余（head/z/out-proj/shared+quant/rec/ab/conv/PCIe/copy 等） | 16.7 | 30.1% |

### 11.2 排期（按上限排序，不再按"看起来新"排序）

| 序 | 编号 | 内容 | 上限 | 判据 | 停生产 |
|---|---|---|---|---|---|
| 1 | **F1** | `fused_gr::gr_down_v3`（256 VGPR + 956 B 溢出）occ 钉 1 / LDS 覆盖 | HC 12.8% | decode >= +2%，parity 全过 | 45 s |
| 2 | **F2** | `kv-grow` 释放 K/V 3.35 GiB，换 +1487 专家槽（+15%） | 专家流 32.2% | decode >= +2%，无换出 | 5 min |
| 3 | **F3** | 路由 fp64 治理（`router_top10.cu:220-226`） | router 7.0% | decode >= +1%，parity 位等 | 45 s |
| 4 | **F4** | dense Q8 GEMV 按形状扫（NW/ROWS/BPI，方法借 routeK `dense_gemv:787-802`） | 11.2% | 逐形状 >= +3% | 45 s |
| 5 | **F5** | `native_mmvq` upstream 布局（`:1157` 从未计时，加 env 双向 A/B） | 未知，最便宜 | 两向都测，无差异维持现状 | 45 s |
| 6 | F6 | A1 Q8 量化 Q + dp4a / DPP 归约 / `v_exp_f32` | attention 3.8%，实得 <= 1% | 前五项完成后才考虑 | 45 s |

### 11.3 关闭清单（附理由，避免以后重试）

- **routeK FA 本体**：稠密 vs 我方块稀疏、V int4 旋转 vs fp16、自有 pools vs paged
- **GQA 打包 / KV 切分合并 / gather 融合 / paged 直读 / persist**：我方已具备或结构不适用
- **MoE 解码 GEMM 六项重排**：它全部实测关闭（V1 2.2x 慢、NPT=2 墙钟中性、V3/V4 DEAD-END、gemm2 NEUTRAL、K-split 2.4-4.2x 慢）
- **MoE 预填 BM 分档**：我方预填 GPU 利用率 0%，前提不成立
- **双缓冲权重预取**：它实测 256 VGPR + 重溢出 5.8x 慢
- **topk 单波内核**：我方 `router_top10_wave_kernel` 已有（31 VGPR / priv 0）；它的 LDS 版与 width-64 版都更慢
- **dense W4A16 自制 GEMV / lm_head 杠杆**：它实测 87-97% 地板、已在地板
- **llama.cpp 跟 master**：`grep gfx906` 两版逐行相同（只有行号位移），GCN tile 表未变；master 唯一差异是 `prec_src1` 参数（我方 4 参调用编不过的根因）
- **gfx906 的 dp4a**：Strata 的 `hip_compat` 虽无 gfx906 分支，但反汇编实测 `native_mmvq` 27,384 条 / `iq_kernels` 43,110 条 `v_dot4`，已由编译器吃成硬件指令
- **dot2 / bf16**：gfx906 无 bf16 dot；我方权重非 fp16
- **routeK CPU MoE**：`dynamic_4bit_int_moe_cpu.cpp` 逐字 "only available on AArch64"，x86 是桩

---

## 12 排期唯一入口（2026-10-25 04:5x 二次收口；**15:4x 三次收口见 §12.5**）

> **【2026-10-25 15:4x 三次收口，优先级最高】** 本节 R1-R8 的排序建立在 **decode** 的 stage 账上，而 decode 只占 M 档墙钟 **10%**、L 档 **0.5%**。
> 首次测出 prefill 的 21 个相位后（`W792`），排期改为按 **prefill** 排：**P1 已采纳（`STRATA_HIP_PROMPT_F16=1`，M 档 prompt -20.7%）**，
> `R5a-down` 撤回（前提不成立），R3/R5b/R6 降级。**以 §12.5 为准**，本节以下 R 批只作历史记录与"为什么关"的依据。

本文历史上出现过**五套**批次编号（C/D/E/F + `W785` 的 Q）。现在唯一入口是 **`W786_TARGET_CORRECTION.md`**（队列 R1-R8）。

**这一版不只是换表，是换目标。** 前五版全部在优化 decode，而三档端到端实测是：

| 档 | prefill | decode | prefill 占墙钟 |
|---|---|---|---|
| S 2.8K | 6.5 s | 4.9 s | 57% |
| M 21.8K | 44.4 s | 5.1 s | 90% |
| L 99K | 211 s | 1.1 s | 99.5% |

=> decode 提速 10%，在 M 档只值端到端 **1%**。

新队列按端到端收益排：

- **R1 撤销（2026-10-25 05:4x，见 `W787_R1_FAILURE_REVIEW.md`）**：补丁已实现并上过生产（镜像 `0.2.4r1`，日志每请求 `1 checkpoints`），但**零收益**——存下的整段 checkpoint 在 park 时被 `drop_superseded` 删掉（`generate.cpp:9492`）；更要紧的是**前提不成立**：真实多轮本来就能复用（0.2.4 无补丁下第 2 轮 `reused=7,344`、`prompt_ms 15,330 -> 685`），「8K 以下零复用」是三个测试脚本构造错误的产物。生产已回滚到 `0.2.4`。
- **R5（第一，2026-10-25 15:0x 改判）** HC 分两条，**主攻 down 的 K-split（Q8 化）**：
  - **R5a-down**：把 `STRATA_GR_SPLIT` 的 K-split down（`fused_gr.cu:2303`，上游自称 ~3%/verify window）从"仅 bf16 行（`s_down == nullptr`）"扩展到 **Q8 行**。收益面：同时拿 HC_Q8 的 -3.2% 与 K-split 的 +3%（`P102`）。判据：`hc_down` 3.47 -> <=3.10（-10%），`hc_up`/`total` 不劣化。**注意它会破坏 bit 等价**（上游因此默认关），要过 parity+needle。
  - **R5b-up（备选）**：给 `gr_up_fast_kernel` 补 Q8（`HC_Q8=1` 当前把它 `!q8w` 挡住）。已测余量 -14%（3.44 -> 2.96），收益 **-0.48 ms（-1.0%）**（`P100`）。
  - **已废**：`TILEV`（`AUDIT7 P1-3`：grid 恒 41 < 60 CU，减小 shared 不增块数；T=3.3 时两种 tile 都只有一次 launch）。见 `W789`
- **R3** 量化+dense GEMV 形状扫（decode 内 13.1%）· **R6** 注意力（M 7.2% / L 10.8%）· **R2** 溢出归因（`block_topk_re` 1120 B、`gr_down_v3` 956 B；先证在 dispatch 路径上）
- **R4 关闭（`P101`）**：路由 fp64 —— 生产 `k==10` 走 `native_router_top10`（`layer.cpp:420`），该内核只对 10 个元素做 `expf`+float，**没有 fp64**；`STRATA_HIP_ROUTER_FAST` 实测无效（旁路）。
- **R7 全部不排**：`--prefill-pipe` / `PREFILL_CPU_SHARE` / `--expert-cache-per-layer` / `--prefill auto:16384`（理由见 W786 §4.2）
- **R8** 合规基线

**已落生产（03:5x）**：去掉 `--resident-experts`，交错 A/B + 三档复核 decode +10.5~11.8%、prompt 不减。

**已关**：`--kv-grow`（gfx906 无 VMM，三臂 slots 恒 9901）；`gr_up75` launch_bounds 与 `gr_down_v3` 溢出治理（HIP 下 `up75_on()` 直接 return false；实际在跑的 GR 内核私有段都是 0）；专家流方向（waitB+waitCPU 已从 10.5 压到 1.20 ms，余下 8.88 ms 是显存读带宽地板）。

**基线口径（`AUDIT7 P1-4` / `P97`）**：现存 decode 基线全部测于 `governor=performance`（10-22 至 10-25 06:0x），生产现为 `schedutil`。任何 A/B 必须当场记录 governor 并前后一致；跨 governor 的数字不可直接相减。

### 12.1 判据与可判下限（`AUDIT7` 实测，用 14 条 M 档 90+ 窗口的阶段行统计）

| 指标 | 同会话内极差 | 跨会话偏移 | 可判下限（3 runs 交错） |
|---|---|---|---|
| **`total ms/window`** | ±1.5% | **21%**（45.97 对 55.65） | **不可单独作判据** |
| `hc_down` | ±3.0% | 小 | >= 6% |
| `hc_up` | ±2.6% | 小 | >= 6% |
| `gemv`（`q8+qkv` + `q8+kv-idx` + `q+q-idx`） | ±3.1% | 小 | >= 7% |
| `router+plan+bell` | ±2.0% | 小 | >= 5% |

**关键事实**：同是「M 档 90+ 窗口」，`total` 在 45.97 与 55.65 之间摆（差 21%），而同期 `hc_down` 只差 6%。
`total` 的波动来自专家流与 CPU 等待，不是 GPU 计算本身 —— **用它做主判据，会把不受控因素算进改动里**。
这也是 R5 那次「53.17 对 51.58 差 3%」根本判不了的原因。

### 12.2 各项换算成「可判门槛」

| 项 | 现值（ms，M 档） | 占比 | 门槛 | 折成绝对量 |
|---|---|---|---|---|
| **R5 `up`**（结构余量已测） | 3.44 | 7.4% | >= 10% | 省 0.34 ms（可达 2.96） |
| ~~R5 `down`~~ | 3.47 | 7.5% | — | **暂不排**：对 int8/bf16 完全不敏感（都是 3.47），需 profiler |
| R3 GEMV | 6.04 | 13.1% | >= 7% | 省 0.42 ms |
| R4 router | 3.75 | 8.1% | >= 5% | 省 0.19 ms |
| R6 注意力 | 3.30 | 7.2% | >= 6% | 省 0.20 ms |

=> **排序不变（HC 仍第一，因为它同时是最大项且门槛最容易达到），但每项都多了一个"达不到门槛就不发车"的前置判断。**

### 12.3 R0 已完成（2026-10-25 13:56-14:19，见 `W790`）

**基线（`schedutil`，HC_Q8=1，M 档 97 窗口）**：total **47.19 / 47.51**，hc_down **3.60-3.62**，hc_up **3.51-3.53**，
gemv **6.09-6.11**，router 3.81-3.87，attn 3.34-3.36，专家流 10.35-10.55（`P98`）。

**两件顺带解决的事：**

1. **governor 差异已量化**：同进程交错 3 对，`performance` 中位 47.03 vs `schedutil` 45.94 = **schedutil 快 2.3%**，
   三对全部同向（`P97` 更新）。所以把 W776 遗留的 `performance` 改回 `schedutil` **不是回归而是改善**；
   现存 performance 时代基线（`P91` 46.35、`W788` 51.58、R5 53.17/53.02）**偏悲观约 2%**。
2. **R5 那个"+3% 回归"被解释掉**：它与 governor 偏差（2%）+ 预热偏差（3%，见 §12.4）同量级，本来就不该判成回归。

### 12.4 测量协议（新增两条，硬性）

- **丢弃重启后前 2 个请求**。实测：第 1 次请求专家流 17.44（稳态 10.3）、total 54.86；第 2-3 次 47.5/47.2；
  同一配置在第 4-9 次为 45.7-46.7。`--expert-cache auto` 是按请求逐步填充的，**不丢弃则基线偏高约 3%**。
  过去所有"3 runs"（含 `P91`）都可能含 1 个偏冷样本。
- **A/B 必须同会话交错**，并在每臂记录 governor。跨会话的 total 摆 45.7-47.5（约 4%），同会话内只 ±1.5%。
- **规则 I（`W791` 第三次踩到）**：**env 生效 != 在路径上。** 开关打开却没变化时，先 `grep` 调用点，确认没有被 `if (X) native_*()` 之类的前置分派挡掉；判据看**该阶段的 ms 有没有动**，不动就是没走那条路，别再花第二次重启复测。
- **规则 J**：动内核前先查上游有没有**已经实现但默认关**的等价路径（`STRATA_GR_SPLIT`、`STRATA_HIP_ROUTER_FAST`、`gr_up75` 都是），读它的默认关理由再决定是"打开"还是"改写"。

§5/§9/§10/§11 与 `W785` 的 Q1-Q9 都不再执行；两代编号到 R 批的映射见 W786 §6。

### 12.5 三次收口：主战场改为 prefill（2026-10-25 15:4x，依据 `W792`）

**为什么改**：三次收口之前的所有批次都在优化 decode，而 decode 只占端到端 10%（M）/ 0.5%（L）。
`W792` 用 `STRATA_PREFILL_TIMING=1`（零代码）首次量出 prefill 的 21 个相位，得到两条判决性事实：

1. **量级**：prefill 里最大的单项是 `hc read` 17-18%（M 8.10 s / L 36.96 s）；而 decode 里同名的 `hc_down` 只值 M 档墙钟 0.7%。**同名不同物，差 21 倍。**
2. **可判性**：prefill 相位 4 次极差 **0.14-0.24%**；decode 相位 3-runs 可判下限 **6-7%**。同样的成本，在一处能判 0.3%，在另一处判不了 3%。

#### 新队列（按 M 档墙钟排；括号为门槛）

| # | 项 | 靶 | 状态 | 判据 |
|---|---|---|---|---|
| **P1** | `STRATA_HIP_PROMPT_F16=1` | 46% 的 prefill 走 rocBLAS bf16→f16 | **已采纳 15:37**（M 档 `prompt_ms` 45,286 -> 35,917 = **-20.7%**；needle 2/2；上溢 0） | 已过 |
| **P2** | rocBLAS 解题表接上 gfx906 | P1 之后的那 33% rocBLAS GEMM | **排队**（`P105`）| 只换解不改算术 => bit 一致 + `GPU timeline` >=3% |
| **P3** | `-mllvm -amdgpu-sched-strategy=max-ilp` | 全 prefill kernel | **排队**（社区 Vega 20 报 10-20%）| 重编一次 25 min，1 臂 x 3 |
| **P4** | `STRATA_SELECT_SIMT=1`（`=2` 在 HIP 被静默退路挡，`P106`） | L 档 `qsa select` 6.9% | **排队** | L 档该项降 >=30%，needle 不变 |
| **P5** | `qsa attn`（M 15.5% / L 15.3%）+ 专家 MMQ（M 27.6% / L 25.2%）机理 | P1 之后的两大项 | **只做机理**（roofline + profiler），不做实验 | — |
| **P6** | decode 专项（hc_down launch 结构 / GEMV / 路由） | decode 整体 | **降为最低**：全做完约 1-2% 墙钟 | 仅在 decode 占比要提升时 |
| — | **R5a-down 撤回** | — | **作废**：Q8 的 down 本身就是 16 片 K 切分，GR_SPLIT 是 5 片（变粗），不是新增能力 | `W792 §6` |
| — | R1 / R4 / 路径 A(TILEV) / `GR_SPLIT` / `HIP_ROUTER_FAST` | — | 已关（`W787`/`P101`/`W789`/`P102`） | — |

#### 采纳后的相位重排（M 档，instrumented，35,372 ms）

| 相位 | ms | 占比 | 与 P1 前 |
|---|---|---|---|
| gemm gate/up（专家 MMQ） | 7,083 | **20.0%** | 未动 |
| qsa attn | 6,908 | **19.5%** | 未动 |
| gemm down（专家 MMQ） | 3,800 | 10.7% | 未动 |
| gdn | 3,718 | 10.5% | 6,105 -> 3,718 |
| hc read | 3,501 | 9.9% | 8,199 -> 3,501 |
| gdn recurrence | 2,462 | 7.0% | 未动 |
| qsa proj | 1,757 | 5.0% | 2,621 -> 1,757 |
| gdn out proj | 1,623 | 4.6% | 2,146 -> 1,623 |
| dequant | 1,402 | 4.0% | 未动 |
| router+shared | 1,057 | 3.0% | 1,852 -> 1,057 |
| qsa select | 716 | 2.0% | 未动 |

=> **P1 之后，专家 MMQ（34.7%）与注意力（19.5%）成为前两名**；剩下的 rocBLAS GEMM 仍有 33%（`gdn` 10.5 + `hc` 9.9 + `qsa proj` 5.0 + `gdn out proj` 4.6 + `router` 3.0），P2/P3 都打在这里。

**判据口径修正（规则 M）**：门槛按「相位 × 后端」给 —— **decode 相位 >=6%**（`AUDIT7`）；**prefill 按相位细分**（`AUDIT8` 更正：原写「prefill >=1%、极差 0.2%」只挑了两个最平的相位）：
`hc read` / `gemm gate/up` / `gemm down` **>=0.5%**、`qsa attn` / `gdn` **>=1.5%**、`dequant` **>=3%**、prefill 总量 **>=0.8%**（实测极差依次 0.14-1.4 / 0.80-0.91 / 2.6 / 0.33%）。
不再有"全系统一个门槛"的说法。

### 12.6 四轮收口：P2/P3 落地，P4 否决（2026-10-25 16:4x，依据 `W793`）

§12.5 的 P1 之后，本轮把 P2（rocBLAS 解题表）与 P3（max-ilp）都做完了，并把 P4 判掉：

| # | 项 | 结果 | 判据 |
|---|---|---|---|
| **P2** | rocBLAS 解题表 | **采纳**：M 档 `prompt_ms` **-3.0%**（34,421 vs 35,478）▸ **`AUDIT8`：4 个 base 样本下是 -1.8%（中位）/ -1.9%（相位 hc read -20.6%）；原 -3.0% 只取了 A 臂两个高样本，总量口径不可判** | 表 56 行/47 有解；`hc read` 3305→2625；needle 32k FOUND |
| **P3** | `-mllvm -amdgpu-sched-strategy=max-ilp` | **采纳**：原记 -1.7%~-3.6%▸ **`AUDIT8`：-1.7% 是跨会话 n=1 对 n=2，落在已实测 2.8% 漂移内 ⇒ 不可判，只能记「方向未否证」** | 只改指令调度；needle 两次 FOUND |
| **P4** | `STRATA_SELECT_SIMT=1` | **否决**：-0.36% = 噪声（A 自身极差 0.33%） | `qsa select` 只占 M 1.9%；`=2` 在 HIP 被静默退路挡（`qsa_select.cu:1838`） |

**镜像**：`strata-gfx906:0.2.4p3`（= 0.2.4 + gfx906 的 rocBLAS 接线 + max-ilp，构建 129 s）。
**env 6 项**：新增 `STRATA_ROCBLAS_TUNING=/data/gfx906-rocblas-5.5.0.txt`。
**M 档累计**：45,286 → **33,437 ms**（482 → **652.8 tok/s**，墙钟 50.6 → **39.4 s**）= **-26.1% / -22.1%**。
**合规**：`verify_config` PASS=30 FAIL=0；`gen_config --live` 无差异。

**新的相位排序（P1+P2+P3 之后，M 档）**：`gemm gate/up` 20.6% / `qsa attn` 19.7% / `gemm down` 9.9% / `gdn` 10.7% /
`hc read` **7.6%（3,308→2,625 后）** / `gdn recurrence` 7.0% / `dequant` 4.1% / `gdn out proj` 4.8% / `qsa proj` 5.1%。
=> **前两名合计 40%，全是自研 kernel（专家 MMQ + 注意力）；rocBLAS 这条路已经走到 73% 峰值，剩下的都是内核工程。**

**P5 的入口条件（下一轮从这里开始）**：
1. 先量 `qsa attn` 的 roofline：M 档 6.8 s / 21.8K token = 315 µs/token；按 dense 上界（12 个 QSA 层 × 8192² / 2 × 256 × 24）约 4.9 TFLOP/chunk ⇒ 实测 ~2.1 TFLOPS =**fp16 峰值的 8%**。
   **先把"带宽 vs 算力"这一刀切开**（选中的 cell 数 × 256 × 2 × n_head_kv 的字节数 / 805 GB/s），再决定写 tiled kernel 还是改 KV 布局。
2. 专家 MMQ 20.6%：`STRATA_PREFILL_MMQ=1` 已在编译面；先确认它跑的是哪条 MMQ 变体、以及 gfx906 上 `__builtin_amdgcn_sdot4` 是否在用（`P38` 的结论是 dot4 62,596 / dot8 0）。


### 12.7 五轮收口：P5 第一项（注意力）—— 只捞到 -2.7%，其余是内核工程（2026-10-25 17:4x，依据 `W794`）

| 项 | 结果 |
|---|---|
| **P5 前提核查** | `qsa_prompt_attn.cu` 的五个 prompt 内核**全部**调用 `mma16816`，而它在 HIP 下是 `__trap()` ⇒ `#if defined(STRATA_HIP_GFX906) return false;` **是必须的，不是 bug**。"已实现但被一行挡住"在此不成立 |
| **唯一能拿的** | 上游 #1661 的 gfx906 query swizzle（原 `kv_mode == 1` 限定，int8 池）。p4 补丁放开到 KV_MODE 3（k8v4） |
| **实测** | `qsa attn` 6742/6743 → **6202（-8.0%）**；`prompt_ms` → 33,954（总量 -2.7%▸**`AUDIT8`：其中 440 ms 来自 A 臂 `gemm gate/up` 高 5.8%，与开关无关 ⇒ 端到端按相位算 -1.6%**）；除 `gemm gate/up` 外其余相位不动 |
| **否决** | `reduce12`（+74%）；`attn_batch` 32→128（grid 已真并行，只省 launch ≈30 ms/chunk） |
| **剩余** | `qsa attn` 仍占 M 19.0%（6202/32700），实测 ~1.1 TFLOPS ≈ f32 峰值 8%、带宽 4% ⇒ **纯算力受限**。上游 #2220 把同族内核在 Turing 上重写拿到 1.5-4.1x（逐位）⇒ 想再动它必须**写内核**（P5b），预估 3 倍余量、工作量按新 kernel 计 |

**生产现状（M 档，21,827 tokens，无仪器）**：`prompt_ms` **33,200**、**657.4 tok/s**、墙钟 **38.8 s**；
env 7 项（`HIP_PROMPT_F16` / `ROCBLAS_TUNING` / `GFX906_ATTN_QUERY_SWIZZLE` + 原有 4 项）；镜像 `0.2.4p4`。
**累计（P1 之前 45,286 / 482 tok/s / 50.6 s）**：prompt **-26.7%**、吞吐 **+36.4%**、墙钟 **-23.3%**。

**下一轮（P5b/P5c）**：
1. **P5b 专家 MMQ（20.6%）**：先确认 `STRATA_PREFILL_MMQ=1` 下 gfx906 走的是哪条变体、dp4a 是否在用（`P38` 的 dot4 62,596 / dot8 0），再算 roofline；上游 #3857 说明 wave64 的 MMQ 矩阵路径本就是缺口。
2. **P5c 注意力重写**：按 #2220 的思路（少 shared/shuffle、cell-major）为 gfx906 写一个 mode-3 专用 chunk kernel，**逐位**为目标，预期 2-3x ⇒ prefill -12%~-16%。

### 12.8 六轮收口：P5b 专家 MMQ —— dispatch 面耗尽，配置优化到此为止（2026-10-25 18:1x，依据 `W795`）

| 方向 | 结果 |
|---|---|
| **换后端**（`STRATA_PREFILL_MMQ=0`，FP16 专家路径） | **否决 +61.1%**：gate/up 2.73x、down 2.27x、gather 3.54x，其余相位 1.000。FP16 专家 GEMM 只跑到 **3.5 TFLOPS = 峰值 13%**（每专家 ~160 行的小 N） |
| **瓦片宽度**（新 `STRATA_MMQ_TILE_J`，p5 镜像） | **否决**：J=48 +7.2%、40 +7.5%、24 +9.1%、8 +34.6%，单调变差。默认 J=64 已是最优 |
| **分组排序**（`STRATA_MMQ_GROUP_SORT=1`） | **死开关**：引擎逐字 `0 of 48 layers`（`whole_tiles` 全 false） |

**首次量到的事实（引擎自打印，不是推算）**：IQ3_S(gate/up) 与 IQ4_NL(down) 在 gfx906 上被上游启发式选成
**J=64 / 48,000 B per block / smpbo 65,536** ⇒ **只有 1 个工作组驻留 CU**（8 wave / 40 槽 = 20%）。
上游 #28195 的"小瓦片换第二个 workgroup"（+5.86%）前提是 RDNA3.5 的 **128 KiB/WGP**；我们是 **64 KiB/CU**，
换过去只得到"2 组 × 4 wave = 同样 8 wave"，代价是每次权重装入 LDS 摊到的行数减半 ⇒ 净亏。

**roofline 定性**：专家乘积 = M 档 36.4% 墙钟、103 TFLOP / 10,556 ms（两 GEMM）= **9.8 TFLOPS = dp4a 峰值 53.3 TOPS 的 18.3%**（含 gather 11,968 ms ⇒ 8.6 / 16.1%），
而 rocBLAS fp16 稠密在同机是 **19.4 TFLOPS = 峰值 73%**。剩下的 82% 是**内核结构**（hipfire 在 gfx906 上的
PMC 诊断：`LDSBankConflict`/`ALUStalledByLDS` 才是主因；改法 = nwarps=4 + 窗口流式 + 按 mmq_x 的 x_stride + ds_read_b128）。

**规则 O（新增）**：同会话交错 + 每臂 restart 仍有臂位漂移：一次已知 no-op 的臂测出 **1.7%**，`AUDIT8` 复核另见 **2.8%**（W793 的 A 臂总量）与 **5.8%**（W794 的 A 臂 `gemm gate/up` 相位）⇒ **1.7% 是下限**。
**规则 P（`AUDIT8` 立，最高优先级）**：**先用相位判，再用总量旁证。** 一个开关若不能在它声称影响的相位上留下 >= 该相位门槛的变化，就不算生效；
总量差只有在「相位差之和 ≈ 总量差」时才能当幅度依据；凡「总量差 > 相位差之和」的部分，一律记为无关漂移。
⇒ **总量口径只判 >3%**；<3% 必须看相位（prefill 相位 4 次极差 0.2%）。

**结论：本项目第一次"配置面耗尽"** —— `qsa attn`（18.9%）与专家 MMQ（36.4%）合计 **55% 的墙钟，两边都没有开关可翻**。
下一步只能写内核，三个选项按性价比：
**A** gfx906 专用 MMQ 内核（36.4%，分两阶段 5-15% + 10%，单独立项）；
**B** 注意力 chunk 内核重写（18.9%，2-3x ⇒ prefill -12%~-16%）；
**C** 干掉 gather（4.3%，需把 `STRATA_MMQ_DIRECT` 的指针表 MMQ 从 `#if !__HIPCC__` 里放出来，且只对常驻专家有效）。

**生产不变**：`0.2.4p4` / 0.1.49.2 / slots 9901 / vram 606 / env 7 项 / M 档 33,200-33,700 ms（657 tok/s）。
p5（J 旋钮 + tile 日志）**已从生产摘掉**，只作实验镜像保留。

### 12.9 七轮收口：翻案 `SELECT_SIMT`（L -4.8%），并把注意力 roofline 修正 3.7 倍（2026-10-25 18:5x，依据 `W796`）

| 项 | 结果 |
|---|---|
| **`STRATA_SELECT_SIMT=1`** | **翻案采纳**：`qsa select` **M 701->437（-37.7%）/ L 13,963->6,496（-53.5%）**；总量 **L 161,239->153,529（-4.78%）**、M -0.94%；其余五相位逐字不动；needle 3 深度 3/3 |
| **`STRATA_ATTN_LANECELL=1`** | **否决**：`qsa attn` M 6,199->16,704（+169%）、L 29,517->79,077（+168%）——"位一致但更慢" |
| **`P109` 翻案理由** | 原判是「M 档总量 -0.36% = 噪声」：M 上该相位只占 2.1%、臂漂下限 1.7% ⇒ **判据先天看不见**。规则 P 的第一个实战案例 |
| **注意力 roofline 修正** | `W794`/`W795` 的 2.1 / 1.1 TFLOPS 都错（PV 那一路没乘 2）：正确是 **24.1 TMAC / 6.199 s = 3.89 TMAC/s = 14.7% of dp4a（等价 7.8 TFLOPS = fp16 峰值 29%）** |
| **目标重排** | 注意力（14.7%）与专家 MMQ（18.4%）**同档**，且 MMQ 占的时间是它的 1.9 倍 ⇒ **内核工程先做 MMQ**，§12.8 的"先做 B"作废 |

**生产（env 8 项）**：`0.2.4p4` / 0.1.49.2 / slots 9901 / vram 606 / `verify_config` PASS=32 FAIL=0。
**M 32,726 ms（667 tok/s）、L 150,245 ms（662 tok/s）** —— 相对今天起点（45,286 / 215,073）**M -27.7%、L -30.1%**。

**排队（按规则 P 的顺序）**：
1. **SIMT scorer 的选择一致性 harness**（同一批 query 与 warp 内核的 top-k 逐位比）—— 补掉翻案的最后一个风险。
2. **规则 P 重扫**：`STRATA_ATTN_DAILY` / `STRATA_ATTN_MERGE_V` / `STRATA_PREFILL_STREAM_MIN`（都从未测，且都落在某个相位上）。
3. **MMQ 内核**（36.4% / 18.4%）：照 hipfire 的四处改法，分阶段 + needle 门。

### 12.10 八轮收口：gfx906 从不继承 `arch_default_env`，20 个上游开关默认全关（2026-10-25 19:3x，依据 `W797`）

**这一轮改的是"候选池"本身。** `src/core/arch_defaults.cpp` 只对 gfx12 / gfx1151 返回默认表，gfx906 拿到**空表**
=> 上游 20 个 S23/S25/S26 优化在这张卡上默认全关、**从来没被任何人测过**。本次先测其中落在 GDN 那 22.5% 上的四个。

| # | 项 | 结果 |
|---|---|---|
| **P115** | `STRATA_GDN_HEAD=1` | **采纳**：`gdn recurrence` M -28.4% / L -28.6%；总量 M -0.84% / L -1.56% |
| **P116** | `STRATA_GDN_PP=2` | **采纳**：`gdn recurrence` M **-50.2%** / L **-45.6%**；总量 **M -2.62% / L -2.86%** |
| **P117** | `STRATA_GDN_NOY=1` | 否决（无增量：单测注释说明 y 不属于契约，variant 0 本就不写） |
| **P118** | `STRATA_GDN_CONVL2=1` | 否决（更慢 +0.96%/+0.43%，`gather` +103.8%） |

**判据方法论（规则 Q，本轮最大产出）**：一个开关"上游没给我们的架构设默认"有三种原因 ——
(a)只验证过别的架构（**可用**，判据 = 仓库里的 parity 单测，在目标卡上跑一次，**5 秒**）；
(b)依赖特定硬件（不可用，编译成 `__trap()` 或需要没有的库）；(c)真的更差（必须引擎 A/B，4 分钟/臂）。
**先找单测，再决定要不要跑引擎。** 本轮 `GDN_HEAD` 走(a)（`gfx906_gdn_rec_head` 单测 5 秒定案，
PP=0/1/2 三档全 `FAILURES: 0`，2.41x > 1.88x > 1.68x，**预演了引擎结果**），`GDN_CONVL2` 走(c)。

**完整 21 相位对账**：八个臂的"相位差之和 vs GPU 实差"全部闭合到 2 ms 内（C/M -854 vs -853，C/L -4,378 vs -4,377）。
同时暴露一个新现象：**相位标签会迁移** —— C 臂 M 省下的 1,212 ms 里有 328 ms 从 `router+shared`(+175)/`embed+steps`(+93)/
`gdn out proj`(+60) 涨回来。规则 P 只保证"该动的动了"，不保证"只有它动了"。

**生产（env 10 项，无仪器）**：M **31,408 ms / 695.0 tok/s / 36.3 s**、L **144,867 ms / 686.1 tok/s**；
needle 32k 深度 10/50/90% = **3/3 FOUND**；`verify_config` **PASS=34 FAIL=0**、`--live` 无差异。
**累计（09:00 起点 M 45,286/482、L 215,073/462）**：**M -30.6% / +44.2%、L -32.6% / +48.5%**。

**下一轮（队列重排）**：
1. **decode 侧 10 个开关**（`Q8_PACKED`/`Q6_PACKED`/`MMVF_ROWS`/`EXPERT_V2`/`TSUM`/`LFUSE`/`GDN_SPLIT`/`QFUSE`/`PLE_BATCH`/`SH_STREAM`）——
   单轮 prefill 下 decode 只占 M 10%，但**多轮对话场景 decode 才是主项**，要按"多轮"单独排一轮。
2. **prompt 侧剩下四个**：`PF_HCDOWN`（`hc read` 8.1%）、`PF_GEMM`+`PF_PAD`（`qsa proj` 5.1% + `gdn out proj` 4.1%）、`CVEC_FUSE`。
   全部按规则 Q 先找单测（`tests/hip/prefill_hcd_exact_parity.cpp` / `prefill_gemm.cpp` 已存在）。
3. **`gdn out proj` 的 +4.5%**（norm 内核换了导致的布局问题）—— 补回来还能再拿 0.3-0.5%。
4. 内核工程（MMQ 36.4% / attn 19%，施工图见 `W797 §6`：BLOCK_SIZE=8 寄存器分块 + 32-bank padding + wave64 归约）。

### 12.11 九轮收口：decode 侧单轮全否，但拿到「decode 端到端不可判」这条方法学（2026-10-25 20:4x，依据 `W798`）

**规则 K 先给了答案**：多轮场景 `reused` 99.8%，第 2 轮 decode 占端到端 **83%**、第 3-6 轮 **64-69%**
（单轮 M 档只有 15%）=> decode 侧确实值得测，与过去七轮"decode 只占 10%"的判断不同。

| # | 开关 | 结果 |
|---|---|---|
| **P115/P116** | （上一轮，prefill）`GDN_HEAD`+`GDN_PP=2` | **已采纳**（M -2.6% / L -2.9%） |
| **P119** | `SH_STREAM=1` | **否决**：慢 10.8%（源码：HIP 跨流 event 比共享专家本身还贵，R9700 62.9→43.4 t/s） |
| **P120** | `Q8_PACKED=1` | **否决**：靶相位 `q8+qkv gemv` +8.1%（生效）、`waitB` +21.6%，且**吃 1912 MiB / -855 槽** |
| **P121** | `EXPERT_V2=1` | **否决**：`VRAM hits` +37.7% / `Q:VRAM hits` +38.6%，`waitCPU` -39.3%（重叠变串行） |
| **P122** | `LFUSE=1` | 无效（相位全平） |
| **P123** | `GDN_SPLIT=1` | **否决**：`rec` **+37.8%** —— 与 prefill 的 `GDN_HEAD/PP`（-50%）**方向相反**（T=1 vs HT=4） |
| **P124** | `TSUM=1` | 无效（相位全平） |
| **P125** | `QFUSE=1` | **未判（PENDING）**：端到端出现 488/2012 ms 不可能值，相位全面 -10~-25% 而 `waitB` +20.7% |

**规则 R（立，decode 侧 A/B 的唯一正确口径）**：**decode 不能用端到端判**。三条独立证据 ——
(a)v1 基准（6 轮都问"数数字"）：draft 自我强化，`decode_ms` 单调降 27%（4,579→3,198）是假趋势；
(b)v2 基准（6 轮问题各异）：同一台机器上"数数字"4,377 ms 对"解释概念"5,465 ms，**轮间差 25%**，不可比；
(c)同一开关（`Q8_PACKED`）两次测量端到端方向相反（一次慢 6.7-38.9%、一次快 2.8%）。
⇒ 必须用 `STRATA_VERIFY_PROFILE=1` 的 `decode GPU stages (ms/window)` 分相位（GPU 事件计时），
注意 **`STRATA_DECODE_TIMING` 不是它**（那一行是墙钟），且 **profiler 会关掉 `SH_STREAM` 的 fork**。

**结构性判据（本轮最大收获）**：把 W797（GDN，胜）与 W798（decode，全败）对照，
`arch_default_env` 里 gfx1151 的 16 项可分为四类：**纯内核结构改进**（在我们这有效）/ **依赖内存与带宽模型**（反向）/
**拿显存换速度**（我们只有 606 MiB 余量，不可行）/ **架构特化**（`PF_*` 在 gfx906 上 `#else return false`，没编进二进制）。
⇒ **以后看到 gfx1151 的默认项，先分类再决定要不要测**；规则 Q 的第(c)类（真的更差）在这里是常态。

**生产未变**：`0.2.4p4` / env **10 项** / slots 9901 / vram 606 / `verify_config` PASS=34 FAIL=0。
（中途一次污染已修：W798e 的恢复脚本 drop 列表漏了 `STRATA_DECODE_TIMING`，已清理并复核为 ABSENT
—— 教训：**恢复脚本的 drop 列表必须按历史全量写**。）

**下一轮（队列）**：
1. **prefill 侧剩下的都不通**（`PF_GEMM`/`PF_PAD`/`PF_HCDOWN` 在 gfx906 上 `return false`；`CVEC_FUSE` 需 control vector）⇒ 已关闭。
2. **`QFUSE` 复测**（PENDING）：须固定 window 数而非固定 output tokens。
3. **`Q6_PACKED`/`MMVF_ROWS`/`PLE_BATCH`**：按四分类，前两个属"拿显存换速度"、后一个属"减 launch"，优先级低。
4. **内核工程**（唯一的真机会）：专家 MMQ 36.4%（18.4% dp4a）、注意力 19%（14.7% dp4a），
   施工图见 `W797 §6`（BLOCK_SIZE=8 寄存器分块 / 32-bank padding / wave64 归约）。

### 12.12 十轮收口：多轮场景的真地板是「每轮 900 ms 与 token 数无关」（2026-10-25 21:4x，依据 `W799`）

**为什么改靶**：`W798` 已量出多轮 decode 占 64-83%，但**prompt 侧的增量 token 单价没人算过**。算完发现：

| read | prompt_ms | ms/token | 对冷读 |
|---|---|---|---|
| 46 | **917.8** | **19.95** | **13.8×** |
| 237 | 2,187.9 | 9.23 | 6.4× |
| 1,008 | 4,155.8 | 4.12 | 2.9× |
| 1,954 | 4,345.4 | 2.22 | 1.5× |
| 冷读 7,581 | 11,517.2 | **1.52** | 1.0× |

单价单调下降 ⇒ **截距约 900 ms 与 token 数无关**：46 个 token 花掉冷读 694 个 token 的时间。
`read=16` 那档 (569 ms) **根本没有 `strata prefill timing` 行** ⇒ 不走 prefill chunk 路径，是请求级开销。

**地板的一半是 KV snapshot**：引擎逐字 `parked 7589 tokens in 222.9 ms; snapshot_bytes=330210608 reused_kv_bytes=0`
—— 每轮 park 一次写 330 MB 到 RAM、下一轮读回 ⇒ 约 450 ms。默认 `--conversation-cache-park-gain 0` = 每轮都 park，
而源码注释自己说「re-parking writes the whole snapshot only for the next turn to drop it again」。

**实测 park-gain=256**：park 行 8→5、read=108/237/529 **-13.6/-10.8/-10.3%**，但**地板未动**（934 vs 918）、
read=1954 **+3.3%** ⇒ **PENDING（P126），单样本不采纳**。

**三条新挂账**：(a)`reused_kv_bytes=0` —— 增量快照的"保留未改动页"从未生效，每轮全量 330 MB；
(b)`pin=` 机制（`generate.cpp:12735`）专为同前缀兄弟查询设计、**完全不 park**，但需客户端带 `pin=N`，当前前端不配合；
(c)地板剩下的约 450 ms 是请求级（会话匹配/KV 指针重建/首 token），未定位。

**这一轮修正了一个大判断**：今天的 prefill 优化（-30.6%）缩短的是 `1.44 ms/token` 那一项，
而多轮每轮只走 200-500 个 token ⇒ **收益被摊薄**；真正的大头是那 900 ms 地板。
⇒ 下一轮优先 **park-gain 复测（3 次/档，判 >5%）** 与 **地板剩下 450 ms 的定位**，内核工程降级。

**生产未变**：`0.2.4p4` / env 10 项 / slots 9901 / vram 606 / args 无 park-gain（脏参数已清）/
`verify_config` PASS=34 FAIL=0 / `gen_config --live` 无差异。

### 12.13 十一轮收口：多轮地板的真身是「小于 1024 token 的 chunk」，park 不在关键路径（2026-10-25 22:3x，依据 `W800`）

**先纠 `12.12` 的归因。** 把引擎的两层诊断同时打开（`STRATA_TRACE=1` + `STRATA_PREFILL_TIMING=1`，输出在
`/data/strata-huihui-ud-iq4_xs.log`，**不进 docker logs**），一个 read=206 的轮次逐段对账：
read 206 token **1888 ms**（78%）+ checkpoint 80 + refill 37 + windows 53 + 未归因 155 + decode 183 = 2396 ≈ wall 2423。
**park 的 262 ms 不在 t0..t1 之内**（发生在响应交付之后）⇒ 它不占客户端延迟；`12.12` 的「地板一半是 KV snapshot」
不成立，P126 的裁决理由要按「park 线程与下一请求争 CPU/RAM」重写。

**地板在 read 内部的相位分布**（同一会话只变 read）：

| read | 810 | 1588 | 7577 |
|---|---|---|---|
| `wait copy` | **754 ms (23.5%)** | **57 (1.5%)** | **28 (0.3%)** |
| dequant | 380 | 534 | 462 |
| gemm gate/up | 782 | 1025 | 2500 |

断层在 810↔1588。源码 `prefill.cpp:178 kStreamAllMinDefault=1024`：**T<1024 走 routed-only 8 槽环**（拷贝跟每层路由、
无跨层流水），T>=1024 走全流式大环（拷贝被 attention 盖住）。而多轮/agent 的一轮提示正好是 100-1000 token。

**试过并否决 `STRATA_PREFILL_STREAM_MIN`（P128）**：A=1024 / B=128 / C=64 三臂，read 145 → **1851 / 3859 / 4037 ms**
（+108% / +118%），470 → 3219 / 4010 / 3921（+25%），839 → 4078 / **3913** / 3954（-4.0%）。
相位同向：`wait copy` 140 tok 334→1974、250 492→1686。机理＝短 chunk 上「把 512 个专家全搬一遍、每个只服务 0.3 个 token」。
上游 `docs/STRIX_HALO.md:121-131` 逐字同结论（1024 是**独显**上量出的下限；它 3.4→2.1 s/turn 的战绩是 Strix Halo 统一内存）。

**机制级关掉一整族假说**：HIP 探针实测 H2D 4 MB×50 次 —— pageable **12.11 GB/s**、pinned **13.40**、file-mmap 13.16
⇒ **钉页只值 10%，pin / resident 一族（P09 作废 / P66 REJECTED / P71 CANDIDATE）救不了 `wait copy`**，
P66 当年「prompt 不减」终于有机理解释。反推每个 chunk 搬 **2.3-4.5 GB**（580-1100 个 4 MB 专家），带宽已满速。

**P0 正确性发现（P127）**：引擎横幅逐字 `STRATA_ROUTE_TAIL_SKIP=7 is ON (default) … answers differ slightly from 0.1.41`，
而 config 里根本没有这个键。根因是 `decode_defaults_arch_ok()` 的 `#if defined(STRATA_USE_HIP)` —— 本机构建只定义
`STRATA_HIP_GFX906`（P23 早已查实 `STRATA_USE_HIP` 计数=0）⇒ 走 CUDA 分支 `return true` ⇒ 默认开。
**A/B（3 次交错，96 token×3 轮）：decode 合计 5501 vs 5885 ms = -6.5%**（T0 -8.2%、T2 -11.0%、T1 持平），
两臂区间不重叠 ⇒ **留 ON 并显式写死 `STRATA_ROUTE_TAIL_SKIP=7`**（env 10→11），防止上游补宏后无声消失。
代价：它按设计改答案（KL 0.003-0.006），KL 门未做；同根因还有 `arm_cpu_share()`，其余 31 处站点待审计（W801）。

**三条新挂账**：(a)目标环境 VRAM 已挤到引擎安全线以下（`only 506 MiB … add --vram-reserve-mib 832`，现役 768）；
(b)`reused_kv_bytes=0` 是设计（`PR #4002`：slot 直拷路径 `unchanged_tokens` 恒 0），真正的 bug 是
`issue #4081`（Linux/HIP 会话缓存只 park 不 restore，同引擎 0.1.49.2）；(c)无任何 `restored` 行 ⇒ resume 一律来自热批槽。

**生产**：`0.2.4p4` / env **11 项** / 驻留专家 9901 / `verify_config` **PASS=35 FAIL=0** / `--live` 无差异。

**下一轮**：(a)`STRATA_PREFILL_CPU_SHARE` 在 200-800 token 区间重测（P23 只在 T=4 测过，那是 launch-bound 区）；
(b)W801 宏泄漏审计；(c)ROUTE_TAIL_SKIP 的 KL 门；(d)每轮 checkpoint save 65-100 ms + refill 37-218 ms 的减法。

### 13 十二轮：整改之后的新方案 —— 口径先换，再谈优化（2026-10-25 22:4x，依据 `W800`/`W801`/`AUDIT9`）

#### 13.1 先把 KPI 说清楚：两个口径，过去只优化了其中一个

| KPI | 定义 | 现状 | 谁在看 |
|---|---|---|---|
| **KPI-1 吞吐/回归** | 单发 M（21,827 tok）/ L（99,387 tok）的 `prompt_ms` | **31,408 / 144,867 ms（695 / 686 tok/s）**，起点 45,286 / 215,073 ⇒ **-30.6% / -32.6%** | 长文/批量场景 |
| **KPI-2 体验** | 多轮 chat 每轮：TTFT（`prompt_ms`，read<1024）+ decode（答案长度 × 单 token 时间） | read 101/125 → **TTFT 1.48/1.59 s**；read 316/340 → **2.45/2.55 s**；生成 64 token **0.95-1.54 s**（41-68 tok/s）（`W801` 6 臂中位）。一轮普通对话 2.5-4 s，**TTFT 与 decode 各占一半** | 机主实际用法（OpenWebUI 多轮） |

**问题**：KPI-1 的 M/L 都是「>=1024 token 的 chunk」，**结构上看不见 read<1024 这一段**（`W800` 的 1024 断层）。
所以「-30.6%」与 KPI-2 之间没有已知换算 —— 这是本轮之前所有调优的共同盲点。

#### 13.2 剩余空间的四分类（先判有没有，再排先后）

| 面 | 现状 | 结论 |
|---|---|---|
| **参数面** | P103-P128 共 21 项：采纳 8、否决 13（P126 本轮关闭） | **已耗尽**。只剩 3 个从没测过的：`STRATA_PREFILL_CPU_SHARE`（P23 只在 T=4 测，那是 launch-bound 区）、`Q6_PACKED`、`MMVF_ROWS`、`PLE_BATCH` |
| **显存面** | `vram_free` **606 MiB**、请求期最低 **506 MiB**（低于引擎安全线 512，引擎建议 `--vram-reserve-mib 832`）；驻留专家 9,901 / 24,576 = **40%** | **是风险不是机会**：32 GB 里腾不出 GB 级空间，+512 MiB 只换来 +0.9pp 驻留 |
| **内核面** | 小 chunk（read<1024）里 `wait copy` 23-33% + `dequant` 14-16% + `gemm gate/up` 21-31%；decode 里 `VRAM hits` 5.27 / `shared+quant` 1.65 / `router+plan+bell` 2.94 ms/window；MMQ 墙钟 36.4%、dp4a 效率 18% | **唯一还有量级的项**，而且**同一个内核同时服务 TTFT 与 decode**（M=1-4 的 decode、M=4-16 的小 chunk） |
| **上游面** | `0.1.50`（v0.2.5）对 Qwen 引擎：`src/prefill/` **0 文件改动**、`generate.cpp` 只改 `--adapt-async` 默认（CUDA/arena 专用）、CPU 专家核 `iq_avx512/native_expert`；`#4081`（Linux/HIP 会话缓存只 park 不 restore）仍 open；`#4005/#4006` 是 Windows 项；`#3321`（slot↔pool 5.3 GB/s）与我们的 park 同源 | **不升 0.1.50**（对 Qwen 无相关收益）；**不投会话缓存**（restore 这条路在上游坏着） |

#### 13.3 方案（P0 → P4，每条都带判据与退出条件）

**P0（本轮已开头）把 KPI-2 变成唯一裁判**
- 工具：`albus/r5/mt_chat.py`（8K 会话、4 轮 read 80/280/80/280、每轮生成 64 token）、`ab_p15.sh`（每臂断言 `env_n`）。
- (a)**基线已定**（`W801` §3.3，6 臂中位）：PROD 的 TTFT = 1.48/2.45/1.59/2.55 s（read 101/316/125/340），decode 0.95-1.54 s/64 tok。
  (b)**今天 4 项 env 在 TTFT 上是中性的**（-5.3/-0.9/-3.5/+0.9%），decode 合计 -5.3% 但逐轮符号会翻 ⇒ 需要**按单参数拆**
  （`GDN_HEAD`/`GDN_PP`/`SELECT_SIMT`/`RT_SKIP` 各一臂），因为 `SELECT_SIMT`/`GDN_PP` 都是在大 T 上量的。
  (c)**还缺一条**：把 09:00 那套（p3 镜像 + 5 项 env）用同一个 bench 跑一遍，回答「-30.6% 有多少落到体验上」。
- 判据：TTFT 与 decode 分别判，**不许用 wall 合并**（decode 会盖住 TTFT）；每档 n>=3、中位、>5%。
- 退出：4 条单参数曲线出来即收口，写进 register 的 verdict。

**P1 显存安全线（已完成，`W802 §2`）**
- `--vram-reserve-mib 768 → 832`：**采纳**。四臂实测 M 691.6 vs 692.05 tok/s（+0.06%，噪声内），
  而 `only 506 MiB of VRAM free` 告警从 **2/2 臂** 降到 **0/2 臂**；成本 ≈28 个专家槽（0.28%）。收益是消掉 `#2065`
  「decode 掉到个位数 tok/s」的尾部风险。现役请求期最低 506 MiB 已在阈值下方。
- 判据：M 2 样本不劣于 -0.5%，且请求期 `vram_free` >= 560；L 1 样本作旁证。

**P2 内核：per-expert MMQ 在 M<=16 的效率（唯一有量级的项）**
- 靶点（都在同一批数字里）：`gemm gate/up` 393 ms / 206 tok（≈16 µs/专家，M≈4）、`dequant` 275 ms、decode `VRAM hits` 5.27 ms/window。
- 先走 5 秒判据（规则 Q）：查 `tests/hip/` 有没有 MMQ 的 parity 单测；有就先单测，再进引擎 A/B。
- 已封的路不要再走：`MMQ_TILE_J`（P113 全负）、`GROUP_SORT`（P114 死开关）、`PF_FUSED`（gfx906 没编进）。
- 判据：`gemm gate/up` 或 `VRAM hits` 相位 >5%，且 TTFT 与 decode **同向**。

**P3 `STRATA_PREFILL_CPU_SHARE`：已收口 —— KL 门跑完，已采纳 `auto` + 钉 `MAX=1024`（见 §14）**
> 本节以下写于 `W802`（当时卡在 parity），保留作为历史；**结论以 §14 为准**。
- **已做（`W802`）**：read 101/316/125/340 四轮，TTFT **-24.4 / -28.7 / -21.3 / -21.9%**（带仪器，n=3，区间不重叠）；
  无仪器复测 **-26.3 / -25.9 / -26.8 / -22.7%**（n=2）；小 chunk 的 GPU timeline **-26~-45%**；M 不变（694.3 vs 698.0 tok/s）。
- **但 parity 不过**：两题贪心输出从第 3 个字符起分叉（`W802 §1.7`）。P23 在 T=4 看到的「逐 token 相同」是 4 个 id 的巧合。
- **下一步（唯一阻塞）**：`STRATA_LOGPOS` teacher-forced KL（判据中位 <= 0.01，参照 P110/P115/P116/P103 的 0.003-0.01 带）；
  过门则采纳 `auto`；不过门则试固定 share 0.3/0.5，看能否压回带内。

**P4 观察项（不做动作，只挂账）**
- `#4081` 修好之前，会话缓存的 restore 路径不可用；`pin=` 需要客户端配合；`#3321` 的 slot↔pool 5.3 GB/s 与我们 park 的 1.4 GB/s 同源（都是 per-layer 串行）。
- 这些一旦上游动了，会话缓存的收益会突然从 0 变成「每轮省一次全量重读」—— 值得每轮同步时看一眼。

#### 13.4 明确不做（附理由，防止反复）

| 项 | 理由 |
|---|---|
| `STRATA_PREFILL_STREAM_MIN` | read 145 时 **+108%**（P128） |
| `--conversation-cache-park-gain` | 只在 read≈277 赢，read<150 是 **+3.1%**（本轮 P126 关闭） |
| `pin=N` | 请求级参数，前端不带（`generate.cpp:12735`） |
| `--resident-experts` / `--resident-cpu-experts` / `STRATA_RESIDENT_PIN` | H2D 探针 pageable 12.11 / pinned 13.40 GB/s ⇒ 钉页只值 10%，机制上救不了 `wait copy` |
| decode 7 开关（P119-P125） | 全否，且 `Q8_PACKED` 吃 1,912 MiB |
| 升级 0.1.50 | Qwen 侧无相关改动（`src/prefill/` 0 文件） |

#### 13.5 判据总表（本轮之后一律照此）

| 变更类型 | 判据 | 样本 |
|---|---|---|
| TTFT/多轮 | `prompt_ms` 中位 **>5%**，按 read 分档 | 每档 n>=3、交错 |
| 吞吐 M/L | `prompt_ms` 中位 **>1%**（M/L 分辨力 0.2%，但臂漂 1.7%） | n>=2 |
| decode | `decode GPU stages` 单相位 **>5%**；端到端 decode_ms 只作旁证（噪声 27%） | n=3 取中位 |
| 任何"方向反转" | 必须重跑 3 样本（规则 V） | — |
| 配置类 | `verify_config` FAIL=0 且 `--live` 无差异；每臂断言引擎真实 `env_n` | 每次 |

### 14 十三轮：P3 收口 —— CPU share 采纳，KPI-2 从 1.48/2.45 s 降到 1.03/1.56 s（2026-10-26 00:2x，依据 `W803`）

#### 14.1 做了什么

`W802` 发现的 -25% TTFT 一直卡在「它改答案」上。本轮把质量门造出来并跑完：

**机制上的硬约束**（这是本门的全部难点）：
- `prefill.cpp:2882` CPU share 只在 `!stream_all` 的 staged prefill chunk 上生效（`T >= stream_all_min()` 就不用它）；
- `generate.cpp:9543` `STRATA_LOGPOS` 只在 **verify 窗口**（解码路径）落行，判定在 `generate.cpp:12918`。
⇒ **「被 CPU 算过的 token」和「能被打分的 token」永远不是同一批**。于是把门拆成**注入**与**测量**两段：
脚本化 15 轮对话，shape 轮 fresh 551–617 token（> `--short-read 300` 且 < 1024 ⇒ staged prefill ⇒ CPU share 写 KV），
probe 轮 fresh 141–187 token（<= 300 ⇒ 窗口 ⇒ LOGPOS 落行，读到的是**被污染过的 KV**）。判的是**下游分布**。

#### 14.2 结果：判据换成「开关差 <= 同配置两遍」

| | 15 个 `STRATA_PREFILL_CPU_SHARE` 臂 | KL 均值 | argmax |
|---|---|---|---|
| A∥C（`share=0` 跑两遍，两次装载） | | **0.000000**（md5 相同） | **100.00%** |
| off-vs-on（A 对 B/D/E/F） | | 0.00915 / 0.01090 / 0.01164 / 0.01481 | 92.4–93.7% |
| on-vs-on（B/D/E/F 六对） | | **0.00778 – 0.01134** | 93.3–94.4% |

**区间重叠（0.00915 < 0.01134）** ⇒ 「开与关的差」落在「开与开的浮动」之内；注入前两轮四对**恰好 0.00000**；
逐轮看 t3→t11 注入 2→6 次也不放大（0.008–0.014），**不累积**。
上游同一结构：`DETAILS.md:1891` 表里 CPU_SHARE 行 `0.0006-0.0007` 与「same engine run twice」的底噪同值；
`DETAILS.md:1821` 自报 "mean KL against the share off 0.004 (max 0.025)"。

#### 14.3 采纳

| 项 | 前 | 后 |
|---|---|---|
| `STRATA_PREFILL_CPU_SHARE`（P23） | `0` | **`auto`** |
| `STRATA_PREFILL_CPU_SHARE_MAX`（P129 新立） | 未设（显式 `auto` 时上游缺省 **3072**，`prefill.cpp:220`） | **`1024`** |

钉 1024 的理由：`cpu_share_max()` 同时被当 `g_stream_min_share` 用，会抬高 `stream_all_min()`；
缺省 3072 会把 1,024–3,072 的 chunk 也改成 staged，而**这一段本卡从未测过**（W802/W803 的 chunk 都 < 1024）。
上游在 5070 上 `3072` 于 2048 token「lost 2%」。⇒ 先钉回上游 0.1.41 实测过的范围，3072 另立臂（§14.5）。

生产：env **11 → 12** 项 / `verify_config` **PASS=36 FAIL=0** / `--live` 无差异 / 容器内 environ 12 项逐字可读。

**KPI-2 新基线**（`mt_chat`，8K 会话，两次连跑取中位）：

| 轮 | read | 旧（11 env） | 新（12 env） | Δ |
|---|---|---|---|---|
| T0 | 101 | 1,476 ms | **1,032 ms** | **-30.1%** |
| T1 | 316 | 2,453 ms | **1,564 ms** | **-36.2%** |

⇒ `§13.1` 那张表里的「read 101/125 → 1.48/1.59 s；read 316/340 → 2.45/2.55 s」**全部作废**，以本节为准。
一轮普通对话从 2.5–4.0 s 降到约 1.9–3.0 s。

#### 14.4 代价与新纪律（规则 X）

`auto` 的份额是**按墙钟逐层测量**后分配的，所以**同一个请求在不同的运行里会被切成不同样子** ——
本车四个 `auto` 臂的 md5 全不同，而两个 `0` 臂 md5 相同，把这条钉死在实测上。

⇒ **规则 X：`share=0` 才存在「self = 0」的底噪。**
从此 (1)任何质量门每臂 **n >= 2**，并报「同配置两遍」的底噪；(2)判据写成「变更臂 vs 基线臂 <= 同配置两遍」，
不再用绝对阈值（KL <= 0.01 那套只适用于**确定性**开关，如 P103/P110/P115/P116）；(3)要位一致时临时把 share 打回 0。

#### 14.5 下一步（顺序变了）

1. **P129 `SHARE_MAX` 1024 / 3072 / 0 三臂，read 1,500–2,500** —— 现在钉的是保守值，1–3K 那一段是「白留的」。
2. **任务级门**（分布层已到顶）：短提示上的可判分小任务集，greedy，A/B 各 20 题，判答对数而非逐字相同。
   这是唯一能回答「有没有变笨」的门；上游 #3923 只有速度、没有质量。
3. **相位账重跑**：`share=auto` 下 `wait copy` 应该几乎消失，`W800` 那张 754 ms 的图**已不代表现状**；
   不重跑就会拿旧图继续找错原因。
4. 暂缓：per-expert MMQ（P2）仍在，但在 TTFT 已被砍掉 30% 之后，它的相对收益变小，让位给上面三项。

### 15 十四轮：`SHARE_MAX` 1024 -> 3072，1-3K 段一次拿到 14-32%（2026-10-26 00:1x，依据 `W804`）

#### 15.1 为什么这轮值得做

`W803` 为了保守把 `MAX` 钉在 1024，但那个变量同时是 `g_stream_min_share`（`prefill.cpp:211`），
所以「钉 1024」等于**让 1,024 以上的 chunk 继续把每个专家都从 PCIe 拉一遍**。而 `W800` 的相位账早就写过：
`read 1,588` 时 `wait copy` 只剩 57 ms —— 那句话是 **`share=0` 世界里**的读数，`W803` 之后已经不成立。

#### 15.2 五臂数据（单发 fresh prompt，每档 3 次，按实测 read 分档）

| read | A（MAX1024，原生产） | **B（MAX3072）** | C（share 0） | **D（只 staging）** | E（MAX4096） |
|---|---|---|---|---|---|
| 196 | -27.5% | -26.1% | 0 | -3.1% | -30.2% |
| 608 | -22.2% | -23.2% | 0 | -2.9% | -24.3% |
| 891 | -21.2% | -23.2% | 0 | -6.5% | -25.0% |
| **1,095** | **-0.3%** | **-31.7%** | 0 | -20.2% | -32.6% |
| **1,203** | **-0.0%** | **-27.3%** | 0 | -13.7% | -27.1% |
| **1,406** | -7.0% | **-25.6%** | 0 | -14.3% | -26.9% |
| **1,820** | -0.6% | **-15.6%** | 0 | -4.2% | -16.5% |
| **2,196** | -1.0% | **-14.2%** | 0 | -5.2% | -14.4% |

**三条结论（这是本轮真正的增量）**：
1. **< 1024 只有 CPU 份额有用**（D 臂 ≈ 0，A/B/E ≈ -20~-27%）；
2. **1-3K 是两件事叠加**：staging 贡献 -20/-14/-14/-4/-5%，CPU 再加 -11/-13/-11/-11/-9%；
   **read 越大 staging 越不值钱，CPU 的价值越稳定**；
3. **拐点在 3,072**（E 的 4096 与 B 逐档差 <=1.5%），正好等于上游缺省。

#### 15.3 质量门（1-3K 段，此前从未测过）

shape 轮 fresh 1,483-1,599（落在 1024-3072）、probe 轮 <=300 走窗口，653 个配对位置。
`cpu gate -> share` 行数 **A 45 / B 185 / C 185** —— A 只有第一个 576-token chunk 进了 share，三个 1.5K chunk 全都没进，
这就是隔离自证。

| 对 | KL 均值 | KL 中位 | argmax |
|---|---|---|---|
| A∥B（改 MAX） | 0.0213 | 0.00357 | 89.43% |
| A∥C（第二份样本） | 0.0297 | 0.00474 | 88.51% |
| **B∥C（同配置两遍 = 底噪）** | **0.0271** | 0.00243 | 88.97% |

变更的两份样本把底噪**夹在中间**（0.0213 < 0.0271 < 0.0297）⇒ 按规则 X 通过；中位 0.0036/0.0047 也在 0.003-0.01 带内。
**但本门比 `W803` 弱，要照实说**：本段 `KL=0` 占 **0.0%**（`W803` 的 <1024 段约一半逐位相同），
因为 t0 那个 576-token chunk 在**所有臂**里都进了 share，A 不是确定性基线。
底噪也从 0.008-0.011 涨到 0.027（chunk 从 600 变 1,500）—— 底噪越大越难分辨真信号，也越难误判。

#### 15.4 采纳

`STRATA_PREFILL_CPU_SHARE_MAX`：`1024` -> **`3072`**（env 仍 12 项）。回滚位 `.bak_w804_max3072`。
生产复核：`verify_config` **PASS=36 FAIL=0** / `--live` 无差异 / 引擎 environ 12 项逐字可读 / `slots 9873` / `vram 668`。

**端到端**（生产配置，单发 fresh prompt）：read 1,330 → **3,130 ms**、1,453 → **3,388 ms**、2,060 → **4,305 ms**；
同请求在 MAX=1024 下是 4,070 ms（read 1,406）与 5,171 ms（read 2,196）⇒ **-16.8% / -16.7%**。
chat 口径（read < 1024）不受影响：read 101 → 990-1,371 ms、read 316 → 1,551-1,584 ms。

#### 15.5 一条被纠正的旧结论

**`P128`（`STRATA_PREFILL_STREAM_MIN`）的否决只对「往小调」成立。** 往大调（1,024 → 3,072）是 **-4~-20%**（D 臂）。
方向不对称：往小调会把 <1K 的 chunk 也摊成「全部专家都搬」，往大调让 1-3K 的 chunk 改成「按路由分阶段搬」。
现行生产经由 `CPU_SHARE_MAX` 顺带实现了这个抬高（`g_prefill` 里的 `g_stream_min_share`），所以不单独设这个变量。

#### 15.6 下一步

1. ~~任务级门~~ **已跑完（`W804 §7`）**：36 道可判分短提示（prompt 529-615 token，答案由生成器自算），
   greedy + `reasoning_effort: none`，三臂 A=`share 0` / B、C=生产配置。
   **按值 34 / 34 / 35（36 题）**；配对不一致 **A∥B = 0/36**，而 **B∥C（同配置两遍）= 1/36** ⇒
   唯一的分歧出现在「同一个配置跑两遍」之间。分辨率 1/36 = 2.8 pp，比上游自认的噪声阈（3/30 = 10 pp）细 3.5 倍。
2. **KPI-2 再定基线**：read 101/316 现在是 0.99-1.37 s / 1.55-1.58 s（与 `W803` 同档），
   但 1.4-2.1K 的 read 从 4.07/5.17 s 降到 3.13-4.31 s —— `§13.1` 那张表需要第 3 次改写（前两次见 §14.3）。
3. **相位账再重做一次**：`dequant` 在 1,866 档从 14%（基线）→ 9%（staging）→ 6%（+CPU），
   `gemm gate/up` 仍是 24-26% 的最大项 —— 下一个靶子应该在这里，不在拷贝。

### 16 十五轮：相位账补到真实 8192 档，找到两条新线索，chunk 尺寸**实测通过但按纪律按住**（2026-10-26 20:1x，依据 `W805`）

#### 16.1 相位账换了主角

`W804` 的相位只到 2,196 token（那一档已经 `staged`）。真机上的大 prompt 是 8192 的 chunk（`stream_all`），结构不同：

| read | gemm gate/up | qsa attn | gdn | gemm down | hc read | dequant | wait copy |
|---|---|---|---|---|---|---|---|
| 1,881 | 22.7% | 7.7% | 8.6% | 10.9% | 8.4% | 6.1% | 0.9% |
| 3,313 | 22.1% | 10.7% | 10.8% | 10.6% | 6.7% | 8.5% | 0.7% |
| 6,152 | **20.6%** | **14.5%** | 10.2% | 9.9% | 7.2% | 4.9% | 0.4% |

**每 1k token 的绝对成本**：gate/up **456 -> 431 -> 351 ms**（越大越省），attn **155 -> 209 -> 247 ms**（越大越贵）。
交叉点 4-5K ⇒ **小 read 的敌人是 dense + MoE，大 read 的敌人是 attention**。
**拷贝问题彻底关掉**：`wait copy` 0.4-0.9% —— `W800` 的「754 ms / 23.5%」只属于 `share=0` + 小 chunk 的组合。

#### 16.2 上游三条（逐条读正文）

| 条目 | 结论 |
|---|---|
| **#4159** 独立 MI50 用户 | F16 + CPU share 在 16k prompt 上 393 -> **498 tok/s（+27%）**、118k 上 363 -> 468（+29%）**复现了我们的两个采纳**；`STRATA_RDNA2_SGEMM=all` 352、`STRATA_EXP_MODE=2` 469 都更差 ⇒ 不必再试 |
| **#4157 / #4158** MMVQ for dense | 170-token chunk 里 **930/1730 ms** 在 dense 投影；`STRATA_PF_MMVQ=1` 让 164-166 token 轮次 **1.88/1.78 -> 1.59/1.54 s（-15%）**，正好是我们 KPI-2 的主区间 ⇒ 登记 `P130`，**要重建镜像**（前置 #4156） |
| **#4119** 两遍 QSA 选择 | 打的是 `qsa select`，本卡只占 0.1-0.4% ⇒ **排除** |
| **#4206** prompt-cache-every | 我们 N=8192=chunk，且实测 restore 在工作 ⇒ **不适用** |

**顺手拿到的质量标尺**：上游同 harness 里「只改 chunk 尺寸 512->1024（纯重排）」= mean KL **0.052**，
而 MMVQ 0.065 / CPU share 0.051 / F16 0.049 —— 我们在 `W803`/`W804` 量的两个采纳开关是 **0.008-0.030**，
**低于**这个「纯重排」参照。⇒ 我们的规则 X 比「和纯重排比」更严，两个结论互相印证。

#### 16.3 chunk 8192 -> 16384：实测 -4.4%，但**按住**

性能（同一 28,878-token prompt，正反两种顺序各跑一次）：A 45,551/43,963/45,429 ms，B 43,446/40,155/43,632 ms，
**两臂区间不重叠，中位 -4.4%，最好 -8.7%**。开关自证从启动块读（不是命令行自报）：
`auto:16384` + `borrows 3299 slots (7.43 GiB)` 对 `8192` + `1969 slots (4.43 GiB)`。

质量（shape fresh 11,003/11,311 => 8192 时 2 个 chunk、16384 时 1 个；473 个配对位置）：
**KL 均值 0.060224 / 中位 0.000338 / argmax 90.9%，而 B∥C（同配置两遍）恰好 0.000000**。

**为什么不采纳**：底噪是 0 ⇒ 规则 X（变更 <= 同配置两遍）对**确定性开关天然失效**，这是**判据缺口**；
绝对口径三个统计量互相矛盾（中位比采纳过的低一个数量级、argmax 同档、均值是采纳带 0.003-0.01 的 6 倍）；
上游把 chunk 几何当**稳定性边界**（`STRATA_PREFILL_EQUAL` 逐字「The chunk geometry changes the rounding,
so it is off by default」）。登记 `P131` = HOLD，并写下结掉它的两条路（prompt>=8K 的任务题；或给确定性开关定绝对带，
先用 P103/P110/P115 回测出标尺）。

#### 16.4 一条被纠正的旧结论

`W800` 记的「无任何 `restored` 行 ⇒ resume 只来自热批槽」**已过时**：现在有 **283 条**
`conversation cache: restored`，等效 **43,796 tok/s**（重读同段 640 tok/s ⇒ 快 68 倍），checkpoint 保存中位 **74.2 ms**
⇒ 一次 restore 只要恢复 >48 token 就回本。**会话缓存这条路在工作是划算的**，`#4081` 至少已被修好。

#### 16.5 下一步（按价值）

1. **重建镜像摘 `#4156` + `#4158`（`STRATA_PF_MMVQ`）** —— 唯一还没落地、且正好打在 KPI-2 主区间的项，上游 MI50 实测 -15%。
   这是独立一轮：要动镜像、要回归、要过 KL 门（上游给了 0.065 / 纯重排 0.052 的参照）。
2. **给「确定性开关」补一条判据**（本轮暴露的缺口）：用 `W803` 的语料回测 `P103`/`P110`/`P115` 三个已采纳开关，
   看它们的中位/argmax/均值落在哪，据此定绝对带 —— 否则 `P131` 这类改动永远无法结案。
3. **attention 是下一个量级**：6K 档 14.5% 且随 T 上升；`qsa select`/`indexer` 几乎为零 ⇒ 优化点在 `qsa attn` 内核本身
   （gfx906 没有 bf16 点积，现走 3xTF32），不是在选择器。

### 17 十六轮：给「确定性开关」立标尺，MMVQ 判负，chunk 16384 判死（2026-10-26 21:0x，依据 `W806`）

#### 17.1 本轮三件事

| 事 | 结果 |
|---|---|
| 上游 #4158（小 chunk 的 native MMVQ）移植 + 实测 | **REJECTED**（chat +34.5%、单发 3/4 更慢；MAX_T=512 全慢） |
| 给「确定性开关」立一把 KL 标尺 | **立成**：已采纳的提示侧开关 = 0.0139 / 0.000 / 92.36% |
| 用标尺结掉 `P131`（chunk 8192→16384） | **REJECTED**（KL 是标尺的 4.34 倍，换 4.4%） |

#### 17.2 镜像管线第一次真正跑通（这是本轮的基础设施增量）

`build024/` 里有 `Dockerfile-0.2.4.pN` + `patches/` + `src/`，一条命令就出镜像（主构建层 `DONE 128.9s`）。
两个此前不知道的事实：(1)**`0.2.4p5` 是个从未被使用的实验镜像**（只比 p4 多一个 `patch_mmq_tile_j.py`，W795/P113 已否决）；
(2)**镜像里保留 `/src` 与 `build-906`**，所以增量 `ninja` 也可行。

`p6 = p4 + #4158`。移植件 `albus/w806/patch_gfx906_mmvq.py` 用 7 个「恰好命中一次」的锚点插入，
自检方式是**改动的增删行数与上游 diff 逐字相同**（+62 / +10 / +2）——这比"看起来对"硬得多。
0.1.49.2 里 `native_mmvq*` 的四个签名与 PR 用法逐字匹配，所以是照搬不是改编；`#4156` 本就包含在 #4158 里。

**换二进制不能 `cp`**：目标文件正在被执行 ⇒ `ETXTBSY`，而 `2>/dev/null` 会把它吞成"看起来成功了"。
必须 `cp → strata.new` + `mv -f`（rename 对忙文件是原子的，旧 inode 继续服务跑着的进程）。

#### 17.3 标尺：0.0139 是什么意思

六臂，全部把 `CPU_SHARE` 钉 0（⇒ 确定性），各摘掉一个**已采纳**的开关，同一份 `W803` 语料、1,348 个配对位置：

| 臂 | 摘掉 | 与基线关系 |
|---|---|---|
| A / F | —（两次装载） | 基线，**A=F 逐字节相同 ⇒ self=0** |
| B | `HIP_PROMPT_F16`（-20.7% prompt） | **KL 均值 0.013867 / 中位 0.000000 / argmax 92.36%** |
| C / D / E | attn swizzle / GDN head+PP / RT_SKIP | **三条都逐字节相同** |

C/D/E 全等不是"开关没用"（`RT_SKIP` 在 decode 上实测 -6.5%），而是**仪器看不到**：
`STRATA_LOGPOS` 的行来自 verify 窗口对**提示位置**的打分 ⇒ **这套门是提示侧仪器**。

于是有两个直接后果：
- `W803`/`W804`/`W805` 三个门**都有效**（改的都是 prefill）；
- **`P127`（`RT_SKIP`）欠的 KL 门不能用它还** —— 解码侧要么另建场景（`--short-read` 调小 + 窗口里带 drafts + 长生成），
  要么只认任务级门。这条债现在被明确登记，不再假装"以后跑一下 KL 就行"。

#### 17.4 MMVQ 为什么在我们这儿是负的

上游 #4157 的 -15% 是相对**它自己的 F32 prompt 路径**（逐字 "dequantizes the GGUF blocks to FP16 into the scratch and runs a
rocBLAS GEMM"）。我们已经用 `HIP_PROMPT_F16`（P103，**-20.7%**）把同一坨开销砍过一次；MMVQ 还要再付
`widen FP16×1 → FP32` + 量化成 `Q8_1`（两趟 kernel），再走 8 列一组的 MMVQ。
在 `T <= 256`、`N ≈ 5120 / 2560` 这种形状上，**两趟搬运比不过现成的 rocBLAS F16 GEMM**。

数据：chat（read 101/316/125/340）C(256) = +10.5 / -3.8 / +1.0 / **+34.5%**，D(512) = +10.8 / **+25.2** / +8.2 / **+26.3%**；
单发（tgt150/220/300/600）C = 1,650/1,530/2,020/1,905 对 A 1,445/1,435/1,745/1,900；D 四档全慢。
**B（p6 + 开关关）与 A 不可区分** ⇒ 移植本身无回归，差异只在开关打开时发生。
噪声照实写：A 与 E 同配置，chat 漂 5.6%、单发最小档漂 27.7%（n=2 无分辨力）⇒ 只读方向一致性。

⇒ **`P130` 关闭**。镜像与移植件保留（F16 路径将来若被改，这条路可以重开）；质量门 `ab_p31.sh` + `kl_corpus4.json` 就绪但未跑。

#### 17.5 `P131` 从 HOLD 改判 REJECTED

| | KL 均值 | 中位 | argmax | 换来的 | 代价 |
|---|---|---|---|---|---|
| 标尺（F16 关） | 0.0139 | 0.0000 | 92.36% | -20.7% prompt | — |
| **chunk 16384** | **0.0602** | 0.00034 | 90.91% | **-4.4%**（且仅 >=8k chunk） | **多挤掉 ~1,330 专家槽（~3 GiB）** |

4.34 倍的 KL 换 1/5 的收益，而且 `W805` 的 bench 每个 prompt 只生成 1 token —— **看不到 prompt 之后 decode 命中率的损失**，
而这张卡请求期 `vram_free` 只有 668 MiB（`§15` 刚把 `--vram-reserve-mib` 升到 832 就为这个）。**关闭**。

#### 17.6 下一步（参数面基本关完，只剩三处）

1. **解码侧的质量仪器**（唯一的方法论缺口）：`P127` 的 KL 债、以及以后任何 decode 侧的改动都要靠它。
   最小可行：`--short-read 1` 让整段走 verify 窗口 + 让模型生成 200+ token（有 drafts 才会触发 skip 决策），再按同样的 KL 口径比。
2. **`qsa attn` 内核**（`§16`：6K 档 14.5% 且随 T 上升；`qsa select`/`indexer` 几乎为零）。
   上游 #4119 打的是 select（已排除），MMVQ 这条路已关 ⇒ **没有现成补丁可摘**，要动就得自己改 kernel 并新建镜像。
3. **decode 侧 `VRAM hits`（5.27 ms/window）+ `router+plan+bell`（2.94 ms/window）** —— 这两项合计占 decode 的约 1/6，
   而 decode 占多轮墙钟的一半（`W801`）。

**明确不再走**：MMVQ（本轮）、chunk 16384（本轮）、`STRATA_RDNA2_SGEMM=all` 与 `STRATA_EXP_MODE=2`（#4159 实测更差）、
`qsa select` 两遍选择（#4119，我们这一项 0.1-0.4%）。

### 18 十七轮：解码侧质量仪器造出来了，三笔解码侧债一次结清（2026-10-26 22:0x，依据 `W807`）

#### 18.1 为什么必须换仪器

`STRATA_LOGPOS` 在引擎里**只有一个写点**：`generate.cpp:13084`，在 `read_windows`（提示读入的窗口循环）里。
生成阶段的 verify 窗口从不调用它 ⇒ **它只量提示侧**。`W806` 里那三个解码侧开关「逐字节相同」不是没效果，是仪器看不见。

`RT_SKIP` 在提示窗口里也几乎不触发：`expert_source.cpp:4853-4862` 要求「**窗口内每一个 token** 都把这个缺失专家排在 rank>=7」，
窗口 60-190 个 token 时近乎不可能；而生产日志里 **96.4%**（31,109/32,256）的缺失专家被跳过，那是**解码**窗口的成绩。

#### 18.2 上游怎么测（逐字引 `docs/DETAILS.md`）

`:1880` — "Teacher-forced KL of the decode path (the default's own greedy text and the default sampled at T=0.8, 28 chat prompts …,
220 tokens each, about 6,000 scored tokens per set, **through the real verify windows with the MTP drafts**)"。
读数（`:1885-1890`）：top-1 一致率 **97.7% / 98.2%**，KL 0.0058 / 0.0032，p99 0.061 / 0.035；**底噪（同引擎跑两遍）0.0006-0.0007**。
任务级（`:1895`）：HumanEval 82 + 30 推理题，"**The runs do not separate the settings**"。
另有一条我们需要知道的豁免（`:1873`）：常驻 >= 90% 时它自己会关掉（"the few misses are cheap there"）——**本卡常驻只有 40%**，正落在设计区间。

#### 18.3 我们的仪器（不重建镜像，两层）

1. **第一层「会不会变」**：6 条 prompt × 约 520 token 贪心生成，`share=0` + `--short-read 0` 做路径隔离，
   **A 与 A2 是同一配置的两次装载**（底噪）。
2. **第二层「变好还是变坏」**：36 题任务门（判答对，不判逐字）。

| 臂 | 分叉条数 | 分叉点（token，未分叉按观测长度封顶） | 隐含 argmax 一致率 |
|---|---|---|---|
| **A∥A2（底噪）** | **0/6** | — | **100%** |
| A∥B（`RT_SKIP` 7→0） | **6/6** | 15/35/69/73/79/205，中位 **71** | **≈98.6%** |
| A∥C（摘 `GDN_HEAD`+`GDN_PP`） | **0/6** | — | **100%（逐位等价）** |
| A∥D（摘 attn swizzle） | 4/6 | 10/21/33/429 + 2 条封顶 545/551，中位 **≈231** | ≈99.6% |

我们的底噪是 **0**（比上游的 0.0006-0.0007 更干净，因为把 `share` 钉了 0、常驻固定），
而 `RT_SKIP` 的 ≈98.6% 与上游独立测的 97.7-98.2% 同档 —— **两个互不相同的仪器给出一致的量级**。

#### 18.4 第二层：准确率没动

| 门 | A（生产） | A2（重复） | B（改） | 配对不一致 |
|---|---|---|---|---|
| `RT_SKIP` 7→0 | 34/36 | 34/36 | **34/36** | **0/36** |
| `attn swizzle` 开→关 | 34/36 | 34/36 | **34/36** | **0/36** |

三臂错的都是同两题（t21 应 4403 全答 4423、t32 应 17 全答 14）——模型能力，与开关无关。

#### 18.5 三笔债

| 债 | 读数 | 处置 |
|---|---|---|
| `P127`（`RT_SKIP`） | 6/6 分叉（中位第 71 token）→ ≈98.6%；任务门 0/36 | **债清**，维持 ADOPTED。原挂的「需一次 LOGPOS 门」**作废**（仪器测不了它） |
| `P110`（attn swizzle） | 4/6 分叉（中位 ≈231）→ ≈99.6%；任务门 0/36 | **债清**，维持 ADOPTED；但它是「改舍入」，**不是** bitwise，别与 GDN 混记 |
| `P115/P116`（GDN） | 6/6 **逐字相同**（≈3,100 token 全等） | **债清**：成对 bitwise 等价的 kernel 替换，质量代价 = 0（单独拆开未测） |

#### 18.6 方法论（这条比结果更长期）

1. **发散不是判据，准确率才是**。单看「文本会变」会把所有数值优化一律判死；单看准确率又可能看不出真退化（36 题分辨率 2.8 pp）。
   两层一起用：先证明它**真的生效**（否则可能根本没触发），再判它**值不值**。
2. **底噪必须真跑**。`A∥A2 = 0/6` 让「6/6 分叉」有了意义；`W805` 的教训（同源不等于可信）在这里的版本是
   「没有底噪的 0% 无从解释」。
3. **一次只摘一个开关**。本轮 `GDN_HEAD` 与 `GDN_PP` 是**成对**摘的，所以结论是「成对 bitwise 等价」，不是逐项；
   这条限制已经写进 register。
4. **`LOGPOS` 与「长生成发散」是互补的两把尺**：前者能算 KL，但只有提示侧；后者是解码侧，但只能给「第一处不同在哪」。
   谁都不能包打天下，用之前先问「这个改动在哪一侧」。

#### 18.7 下一步

参数面到这里基本关完了（提示侧有 KL 门、解码侧有发散+准确率门）。剩下的是**内核**：
`qsa attn`（`§16`：6K 档 14.5% 且随 T 上升）、decode 的 `VRAM hits`（5.27 ms/window）与 `router+plan+bell`（2.94 ms/window）。
动内核要么改源码重建镜像（管线已通，`§17.2`），要么等上游。**在动之前，先把这套仪器当作验收标准**：
提示侧改动过 KL 门，解码侧改动过「底噪 + 任务门」。

### 19 十八轮：「HIP 默认关」那类开关清算完，解码侧被 GPU 计算锁死（2026-10-26 22:3x，依据 `W808`）

#### 19.1 新的一类，而不是一个新的开关

`W806` 的教训是「宏缺失 ⇒ 走进 CUDA 分支 ⇒ 把 CUDA 默认带进来」（被动泄漏，`P127`）。但源码里还有**方向相反**的一类：
函数自己写了 `#if defined(STRATA_USE_HIP) … opt-in … #else … default on …`，于是**我们主动关掉了 CUDA 上默认开的东西**。
写扫描器按括号配平切函数体、比对两个分支的 getenv 三态，在 `src/` 里扫出 **8 个**（`albus/w808/scan_hip_defaults.py`）：

| env | HIP 默认 | 非 HIP 默认 | 处置 |
|---|---|---|---|
| `STRATA_ONE_TOKEN_COMMIT` | 关 | **开** | 测了，−6.3% ⇒ `P134` REJECTED |
| `STRATA_HEAD_MIX_MULTI` | 关 | **开**（且 bitwise） | 测了，−0.3% ⇒ `P133` REJECTED |
| `STRATA_SH_STREAM` | 关 | **开** | `W798` 已测，−10.8% 否决 |
| `STRATA_MTP_PREFILL_SYNC` | **开** | 关 | 我们已经是开 |
| `STRATA_FUSE_HITS` | 关（gfx12 才开） | 关 | 测了，−0.6% ⇒ `P132` REJECTED |
| `STRATA_FUSE_CONVAB` / `FUSE_WAIT` / `GFX12_DEFAULTS` | 关 | 关 | 上游自报 −0.3% / 只量过 sm75 / 我们已显式开 `HC_Q8` |

#### 19.2 为什么三条全平：相位说了实话

`STRATA_DECODE_TIMING=1`（**不是** `STRATA_TRACE`，`generate.cpp:14044`）在现役配置下给的一手解码：

| 项 | ms/window | 占比 |
|---|---|---|
| **GPU-reach wait（纯计算等待）** | **31.85** | **72.1%** |
| per-layer host（plan / actq / jobs / **CPU experts 3.76**） | 4.16 | 9.4% |
| **draft（草稿头）** | **3.82** | **8.6%** |
| **commit / emit** | **0.04** | **0.1%** |
| stage | 0.05 | 0.1% |

`avg T 2.30、1.89 token/window、drafts accepted 94 of 138` ⇒ 解码在吃草稿，且是 **M≈2 的量化专家 GEMV 打满**。
于是：`FUSE_HITS` 折的是 `copy+combine`（旧 stages 行 **0.70 ms**）；`HEAD_MIX_MULTI` 只省 launch；
`ONE_TOKEN_COMMIT` 能省的 `commit/emit` 只有 **0.04 ms**。三条都在错的量级上。

`P134` 还多一层：它实测 −6.3%，不是因为省得少，而是**草稿接受率从 68.1%（94/138）掉到 63.5%（80/126）**，
窗口数 120 对 106 ⇒ 自提交路径改了草稿头看到的状态。机制未查透，判死够了。

#### 19.3 两处纠正（我自己的错）

1. **解码相位的开关是 `STRATA_DECODE_TIMING`**。本轮先用 `STRATA_TRACE=1` 跑了一遍，一行相位都没出（空跑 3 分钟）。
   教训：仪器开关名不要凭印象，先 grep 打印点。
2. **`VRAM hits` 有两个单位**：旧 `decode GPU stages (ms/window)` 行里是 **ms/window**（10.99），
   DT 行的 `per layer-window` 是 **µs**（21.22，×47 层 ≈ 1.0 ms/window）。同一个名字差 10 倍 —— 谁抄进同一张表就会得出矛盾结论。
   这是 `AUDIT9` 那条「列名必须绑定来源」的同类错误，只是这次发生在相位行上。

#### 19.4 解码侧还剩三条路（都有数据）

1. **draft 3.82 ms/window 买 0.89 额外 token/window（68.1% 接受）** —— 唯一还没系统扫过的旋钮：草稿深度 / `--spec-min-p`。
   不重建镜像、成本低，下一轮先做这个。
2. **CPU experts 3.76 ms（8.5%）** 与 `--pcie-frac 0.20` 耦合，是「搬运 vs 计算」的老平衡，可以重扫。
3. **GPU-reach 31.85 ms（72%）** —— 只能改 M<=4 的量化专家 GEMV 内核（要重建镜像 + 回归）。

**参数面到这里正式关完**：提示侧有 KL 门与 `MAX` 折中，解码侧有底噪+任务门，剩下的收益只在草稿策略和内核里。

### 20 十九轮：解码参数面收口 —— 三个「上游说好、本卡不认」（2026-10-26 23:1x，依据 `W809`）

#### 20.1 本轮把三件「有上游先验、本卡从未测过」的事做完了

| 项 | 上游先验（逐字出处） | 本卡实测 | 处置 |
|---|---|---|---|
| `--spec-min-p` 0.70 → 0.50 | A770：0.0=10.4（接受 52%）/ **0.5=12.2/12.0/11.7**（68%）/ 0.7=11.8/11.4/11.6（93%），`A770_SPEED_SPEC.md:243` | **+0.4%（中性）**，同配置两遍 0.1% | 维持 0.70（`P06`） |
| 九开关融合整套（sm_86 表） | sm_86 **+9.6%/+14.6%（8/8）**`DETAILS.md:2435`；P100 七开关 **+14.2%**（36.56→41.76 tok/s，8/8）`OLDER_GPUS.md:100` | **+8.0% / +5.4%（两臂）** | `P135` REJECTED |
| `STRATA_B6_MMVQ_ROWS` | bit-exact，**+0.2..1%** `DETAILS.md:2514` | 微基准 360 组合**中位 0.00%**，76 个超 ±2%（−12.0% ~ +12.7%），bitwise 全过 | `P136` REJECTED |

#### 20.2 为什么 min_p 0.50 是中性而不是提升

`avg T` 2.25→2.83、`tokens/window` 1.86→2.05（**+10%**），但 `ms/window` 37.05→40.80（**+10%**，GPU-reach 29.38→32.18）
⇒ 两边抵掉。**这说明解码的成本几乎严格正比于「窗口里要算的 token 数」**，摊薄发生在专家读取上但不足以抵消 M 变大的计算。
顺带：`--spec 6`（`avg T` 3.9）是 **+11.4%**、接受率 63.8%→47.3% ⇒ **深度方向（更多草稿）在本卡彻底关闭**。

**这一条同时推翻了我自己第一轮的读法**（3 prompt、不丢冷启 → −2.8% 且「4/4 配对都更快」）。
换成 6 prompt 丢前 2 条后是 +0.4%。**冷启被当成了信号**——这是 `P98`（重启丢前 2 请求）在本项目里第二次咬人。

#### 20.3 融合整套为什么在 gfx906 上反过来

这九项的前提是「launch 开销占比大、SM 多、波形切换便宜」。本卡占用率 **6.8%**（`P96`），decode 的 **72%** 是
`GPU-reach wait`（纯等 M≈2 的量化专家 GEMV 算完）；把两个 launch 合成一个不会让 GEMV 变快，而 `SIDE_MIXER=2` /
`ATTN_DAILY=1` 这类「换布局」是按 8.x 的 warp 宽度与 L1 行为量的。

⇒ 立一条通则（与 `W797`「相位会迁移」同构，但发生在**架构之间**）：
**「上游在别的架构上 bitwise + 两位数收益」不能作为本卡采纳的依据。** 采纳前必须在本卡上过同一套仪器。

#### 20.4 方法：分辨率不够就换仪器

| 轮 | 每臂样本 | 同配置两遍差 | 待测效应 | 结果 |
|---|---|---|---|---|
| 第一轮 | 3 prompt（含冷启） | **5.2%** | ~2% | 判不了，且给出错误的 −2.8% |
| 第二轮 | 6 prompt 丢前 2 | **0.1%** | 0.4% | 可判（中性） |
| 第三轮 | 6 prompt 丢前 2 | **6.9%** | ~1% | 判不了（`P` 臂 `per-layer host` 3.00 对 1.67-2.15，host 被干扰） |

**结论**：这台机器上 host 抖动比 GPU 大一个量级（`per-layer host` 只占 9.4%，却能在同配置两遍之间漂 80%）。
⇒ 凡效应 < 5%，**引擎级 A/B 一律不可用**；正解是用上游自带的**微基准**（`b6_mmvq_bench`：GPU 事件计时、50 次中位、
逐格 memcmp、声明 immune to the host）。本轮为此把 `ninja <target>` 这条链打通了（增量 2 分钟，不碰主二进制）。

#### 20.5 一个结构性事实：本卡报 compute capability 9.0

微基准 banner 逐字 `=== device 0: AMD Radeon Graphics (sm_90, L2 8192 KB), 50 reps ... ===`。
同一个 `cudaDeviceGetAttribute` 被 `il_arch_ok()`、`decode_defaults_arch_ok()`、`fused_gr` 等处共用
⇒ **gfx906 在这套构建里被当成 9.0 卡**。这解释了：

- `P127`（`ROUTE_TAIL_SKIP` 默认开）不是偶然，是系统性的；
- 所有 `major >= 8` 的门恒真；
- `nv_default_env(9, 0)` 是空表 ⇒ 融合开关一个都不开（`§20.3` 的直接原因）。

**以后凡是看到「上游按 compute capability 分支」的默认值，都先假定本卡走 major=9 那一支。**

#### 20.6 三条死路（登记完，以后不再花 GPU 时间）

| 项 | 证据 |
|---|---|
| `STRATA_MMVQ_IL_ROWS` / `_WIDE` / `_T1` | `native_mmvq.cu:2941` 的 `#if !defined(__HIPCC__)` 包住整套实现，`:3262` 是 `#else // HIP: no interleaved path` 的 stub ⇒ `native_mmvq_il_supported()` 恒 false（`P137` N/A） |
| suffix draft / `--lookup-chain` 调参 | suffix 每请求只开 **1-2 个窗口**（全请求约 100），接受 0-4/3-6；lookup chain 日志 **0 行** |
| `--spec` 加深（>4） | `--spec 6` +11.4%、接受率掉到 47.3%（`§20.2`）；上游 `DETAILS.md:2492` 也是 4 最好 |

#### 20.7 到此为止：解码侧参数面正式关完

自 `W808` 起，解码侧已按「相位 → 每类旋钮 → 每个旋钮」走完：

| 层 | 结论 |
|---|---|
| 相位 | GPU-reach 72.1% / host 9.4% / draft 8.6% / commit+emit 0.1%（`W808`） |
| 融合（4 个） | `FUSE_HITS` −0.6 / `HEAD_MIX_MULTI` −0.3 / `ONE_TOKEN_COMMIT` −6.3 / 九项整套 **+5.4~+8.0**（全否） |
| 布局 / rows | `B6` 净 0、`IL` 编译掉（全否） |
| 草稿策略 | `min_p` 中性、`spec` 深度负、suffix 可忽略（全否） |

**剩下的唯一量级在 GPU-reach 的 31.85 ms/window（72%）里**：M≈2 的量化专家 GEMV。它要么改内核（管线已通，
微基准链也通了），要么等上游。**在那之前，任何「解码还能快 x%」的说法都必须先落到这张表上。**

### 21 二十轮：AUDIT10 审计 W801-W809（P0=0 / P1=2 / P2=6 / P3=3，含审计者自己一条误判）（2026-10-26 23:4x）

#### 21.1 范围与方法

`AUDIT9` 之后的**全部九轮**（W801-W809）。把 166 上 **46 份原始驱动件**打包拉下来，写**独立解析器**逐字段重算
（`albus/audit10/`：盘点、DT 重算、PH 全字段 + 加总校验、五臂两口径、KL 独立实现），
源码引用逐条 `sed -n` 核对，上游引文回 `docs/` 原文。

**好消息先说**：四次改配置的载荷数值**全部逐字复现** ——
`VRES 768→832`（告警 2/2 → 0/2）、`CPU_SHARE=auto`（8/8 TTFT 值）、`SHARE_MAX=3072`（7/8 行）、
`RT_SKIP=7`（标尺 0.013867 + 分叉 6/6）。**没有一条生产改动建立在错数上。**

#### 21.2 两条 P1

**P1-1 W807：把「删失观测」当数据点，swizzle 的扰动排序算反了。**
`A∥D`（摘 attn swizzle）原文写「10/21/33/429 + 2 条封顶 545/551，中位 ≈231 → ≈99.6%，比 `RT_SKIP` 更晚分叉」。
把「551 token 内未分叉」当成 545/551 两个观测值一起取中位，等于把删失当事件。四个真实分歧点的中位是
**(21+33)/2 = 27** ⇒ 一致率 **96.3%**，而 `RT_SKIP` 是 6/6、中位 **71** → 98.6%。
⇒ **swizzle 分叉更早、扰动更强**；排序从「`RT_SKIP` > swizzle」改成「**swizzle > `RT_SKIP` > GDN**」。
任务门（34/36、同错 t21/t32、不一致 0）已复算，`P110` 的采纳不变。

**P1-2 W805：相位表漏了 `ple`，它是大 read 档的第二大项。**

| read | gemm gate/up | **ple** | qsa attn |
|---|---|---|---|
| 1,881 | 22.7% | **10.4%**（393 ms） | 7.7% |
| 3,313 | 22.1% | **14.4%**（931 ms） | 10.7% |
| 6,152 | 20.6% | **15.4%**（1,617 ms） | 14.5% |

PH 行本身自洽（逐档加总与 `GPU timeline` 差 0-1 ms），是**挑字段时漏了**。受影响的结论：
「大 read 的敌人是 attention」要改成「**attention 与 PLE 同档**」；「剩余靶子」清单要加上 ple。

**这条带出下一轮的第一顺位**（已登记 `P138`）：`ple` = 从第 1 层起等 SSD 读完 PLE 行
（`prefill.cpp:3078` 逐字 "a wait for the SSD read"），生产用 `--ple-io` 的**缺省 `direct`**（无缓冲 SSD 读），
而 `direct|mmap|ram` 都在本树（`generate.cpp:806`）。上游 12.0 卡上「表放 RAM」4K **−18%**、20K −9%。

#### 21.3 六条 P2 与三条 P3（要点）

- **W804 的分档宽度从未声明**（实际 ±25~50）：±25 下 7/8 行 <1pp，`read=196` 那行偏 2.5pp；
- **W804 §5 的「同请求」不是同一请求**（read 1,453 对 1,406；2,060 对 2,196）⇒ −16.8% 混了尺寸差，方向偏保守；
- **`DECODE_TIMING=1` 自身让 decode 掉 15.9%**（50.74 → 42.69），从未记录，也解释了 W802 那个 T0 +37.5%；
- **「W803 约一半位置逐位相同」实为 29.4%**；
- **W806 的四个 off-vs-on KL 未绑臂**（可复原为 `A∥E/A∥F/A∥B/A∥D`）；
- **多处端到端数字只打到 stdout、未落盘**（W804 §5、W806 §2）。
- P3：`native_mmvq.cu:3262` 实为 **3259**；W801 的 Δ 未写「以 PROD 为基准」；
  **W806 §0 摘要没写「TTFT」**——就是这一条让审计者误读、误报了一条 P1。

#### 21.4 审计者自己的误判（已撤回，写进纪律）

第一版把 `W806 §3.1` 的 `T0 TTFT` 列读成 decode，得出与文档不符，报了「MMVQ chat 表不可溯源」。
按 TTFT 复算 **16/16 格逐字命中**，撤回。
⇒ **规则 AB**：审计结论在写进报告前，必须先用独立解析器**按列名**复现一遍；
「复现不出」的第一反应是「我读的是哪一列」，而不是「文档错了」。规则 S 对审计者自己也适用。

#### 21.5 三条规则

- **Y 删失观测不能当事件**（W807 把 96.3% 写成 99.6%）；
- **Z 相位表必须自洽且完整**：字段加总 == `GPU timeline`，且占比 >=2% 的字段一个都不能省
  （已做成可执行检查 `a_w805_phase.py`，会自动标「漏」）；
- **AA 仪器税必须报**：`DECODE_TIMING` 15.9%、`PREFILL_TIMING` 在 W802 里让 T0 decode 偏 +37.5%。

#### 21.6 生产

未改动：`0.2.4p4` / env 12 / `--spec 4 --spec-min-p 0.70` / `--prefill auto` /
`--ple-io` 未设（= `direct`）/ `verify_config` **PASS=36 FAIL=0** / `--live` 无差异。
`P138` 是 CANDIDATE，`gen_config` 不写它（已核 `args` 里没有 `--ple-io`）。
