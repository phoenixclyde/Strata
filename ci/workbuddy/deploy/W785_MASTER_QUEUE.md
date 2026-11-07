# W785 统一队列：唯一排期表（v2，2026-10-25 03:1x 复核后修正）

> **[2026-10-25 04:5x 作废] 本文件的 §1 上限表与 Q1-Q9 队列已由 `W786_TARGET_CORRECTION.md` 取代。**
> 原因：§1 引的 `P87` 是在 `--resident-experts` 开着时测的，且该表分项和（63.45 ms）与总数（74.76 ms）差 15%；
> 更重要的是**优化目标选错了**——decode 只占端到端墙钟的 0.5-43%，prefill 占 57-99.5%。新队列见 W786 §4（R1-R8）。
> 本文件 §2（三处白跑风险）与 §6（纪律）仍然有效，继续引用。
> **[2026-10-25 06:3x 追加] `AUDIT7` 又抓到第三类白跑：`W788` 的「路径 A（TILEV 2560->1280）」源码级无效** ——`DOWN_BLOCKS` 与 TILEV 无关（grid 恒 41 < 60 CU），且我们的 T=3.3 时两种 tile 都只有一次 launch。R5 已按此路径做过一半，裁定见 `W789_R5_TILEV_VERDICT.md`；要治 HC 只能加块数。

> 为什么有这份：`W776` 先后出现 C 批（§5）、D 批（§9）、E 批（§10）、F 批（§11）四套编号，互相覆盖。**本文件是唯一排期入口**；那四节只作历史留档，映射见 §5。
> v2 修正了两条会让计划白跑的判断（§2），队列因此重排。

---

## 1 判定依据

**(a) 上限表（P87，E0 实测，M 档 21,827 token、97 窗口稳态，GPU 55.65 ms/window）**

| 去向 | ms | 占比 |
|---|---|---|
| 专家流（VRAM hits 7.44 + waitB 6.49 + waitCPU 4.01） | 17.94 | 32.2% |
| HC 投影（hc0/hc1 的 down + up） | 7.15 | 12.8% |
| 量化 + dense GEMV（q8+qkv 3.92 + q+q-idx 2.18 + 0.15） | 6.25 | 11.2% |
| router + plan + bell | 3.87 | 7.0% |
| 注意力一族（attention 2.11 + scores+topk 1.61） | 3.72 | 6.7% |
| 其余 | 16.7 | 30.1% |

**(b) 关闭表**：见 `PARAM_REGISTER.tsv` 的 REJECTED/REFERENCE（含 FA 本体、MoE 重排六项、topk 单波、dense W4A16、lm_head、dot2、CPU MoE、llama.cpp 跟版、`pool-tasks`、`ple-inflight`、`host-core`、`aux-cpus`、`prompt-cache-every`、`prefill 4096`、`pcie-frac 0.36`、`SH_STREAM`）。

---

## 2 Review 抓到的两处"白跑风险"（v1 的 Q1/Q2 作废）

### 2.1 `gr_up75_kernel` 在 gfx906 上不执行
`fused_gr.cu:1193-1196` 逐字：

```cpp
bool up75_on() {
#if defined(__HIPCC__)
    return false;
```

=> 它的 `__launch_bounds__(256, 4)` 与 72-88 B 溢出**是死代码的属性**。v1 把它排第一是错的。

### 2.2 HC_Q8=1 时真正在跑的两个 GR 内核，**没有溢出**

按 `launch_multi`（`fused_gr.cu:1242-1330`）推：`q8w = (m.a[0].s_down != nullptr)`，HC_Q8=1 时 q8w 为真 =>
`staged = variant >= kHcStaged && s_down == nullptr` 为假 => down 走 `gr_down_multi_kernel<2560, T, true>`，up 走 `gr_up_multi_kernel<NT, true, true>`。

ELF 实测：

| 内核（实际在跑） | VGPR | 私有段 |
|---|---|---|
| `gr_down_multi_kernel<2560, 8, true>` | 114 | **0** |
| `gr_up_multi_kernel<6, true, true>` | 107 | **0** |
| `gr_down_staged_kernel<6, true>`（HC_Q8 关时的 down） | 122 | **0** |
| 溢出的那两个：`gr_down_v3_kernel<1,6,true>` / `gr_up75_kernel<3,true>` | 256 / 64 | 956 / 80 |

=> **routeK 的"occupancy 钉低换 VGPR、消溢出"在我方 HC 路径上没有对象**：跑着的内核一个都没溢出。HC 那 12.8% 是别的原因（4 个 kernel 每层每窗口的启动与访存结构），不是寄存器压力。

**结论：v1 的 Q1、Q2 撤销。** 这一条如果没复核就开工，会花 55 分钟编两个环境、测出 0 收益，还要再花半小时解释为什么。

### 2.3 `--kv-grow` 在 gfx906 上不可能开启（Q1 实测 + 源码双证据）

- 三臂实测（见 §4）：A0 现行 / A2 去 resident / A1 去 resident + kv-grow，**expert_slots 全是 9901、22841 MiB，一个槽没变**；引擎日志打出 `strata generate: --kv-grow is off (...)`。
- 源码门：`src/core/vmm.cpp:158/167` 把 HIP VMM 整段限定在 `defined(STRATA_USE_HIP) && !defined(STRATA_HIP_GFX906)`，我们是 `STRATA_HIP_GFX906` 构建 => 落到 `:299-303` 的 `vmm_available() { return false; }`。同处注释逐字：`Everything else (Metal, gfx906, ROCm older than 6): no virtual memory, the elastic K/V stays off.`
- 顺带修正 P32 的算术：816 B/cell 是**每层**（`kv_pool_bytes` 的 rows 含 `n_head_kv`，每层一个 pool；hybrid 2 x (256+8x2+144) = 832 B；文档与 `layer.hpp:222` 写 816，按代码算术是 832，差 2%，以运行期为准），P32 原文当成整机总量算出 214 MiB / 93 槽；真实总量按层数乘（W782 引用的源码注释为 262K 上下文 3.35 GiB）。**算术错，但结论更强：不是收益小，是不可达。**
- `--expert-cache` 的 VMM 路径（`expert_cache.cpp:509`）同样不可用。

---

## 3 队列 v2（按"上限 x 可执行性"排）

| 序 | ID | 内容 | 上限 | 类型 | 停机 | 成本 | 状态 |
|---|---|---|---|---|---|---|---|
| **1** | **Q1** | `--kv-grow` + 去 `--resident-experts` | 专家流 32.2% | 配置 | 5 min | 已执行 | **已落生产：去 resident 胜（三档 decode +10~12%，prompt 不减）；kv-grow 因 gfx906 无 VMM 不可达**（§2.3、§4.1） |
| **2** | **Q2** | 路由 fp64 治理：`router_top10_wave_kernel` 的 512 次 `exp(double)` + 串行 double 加（`router_top10.cu:220-226/258`） | router 7.0% | 源码 + 重编 | 45 s | 30 + 20 min | 下一个 |
| **3** | **Q3** | 量化 + dense GEMV 按形状扫（NW/ROWS/BPI；方法借 routeK `dense_gemv:787-802`） | 11.2% | 源码 + 重编 | 45 s | 45 min | 待定 |
| **4** | **Q4** | `native_mmvq` upstream 布局（`native_mmvq.cu:1157` 从未计时，需先加 env） | 未知 | 源码 + 重编 | 45 s | 35 min | 待定 |
| **5** | Q5 | 注意力三项（Q8 量化 Q + dp4a / DPP 归约 / `v_exp_f32`） | 3.8%，实得 <= 1% | 源码 + 重编 | 45 s | 各 30 min | 待定 |
| — | Q6 | 8K 以下对话零复用（`generate.cpp:9903/9907/9930`） | 首字 15 s 级 | **外部**，只报上游 | — | — | — |
| — | Q7 | 合规基线（冻结 fixture / temp 1.0 / top_p 0.95） | 可比性 | 测量 | 20 min | 25 min | — |
| — | **Q8** | **去 resident 后的内存观察**：`pgsteal_file`、`pgmajfault`、`MemAvailable`、swap | 回滚保护 | 监控 | 0 | 常驻 | 进行中：MemAvailable 62.0 GiB、SwapFree 16.77 GB（未换出）；触发线 MemAvailable < 20 GiB 或出现任何 swap |
| — | ~~Q1/Q2 v1~~ | ~~`gr_up75` launch_bounds / `gr_down_v3` 溢出~~ | — | **撤销**（死代码，见 §2） | — | — |

---

## 4 Q1 已执行（结论：不可达），Q2 成为起点

### 4.1 Q1 三臂实测（2026-10-25 03:1x，每臂 5 runs，21,827 token）

| 臂 | 配置 | expert_slots | prompt_tps | decode 中位 |
|---|---|---|---|---|
| A0 | 现行（resident 开，kv-grow 关） | 9901 | 487.9 | 54.6 |
| A2 | 去 `--resident-experts`（kv-grow 仍关） | 9901 | 489.1 | 66.0 |
| A1 | 去 resident + `--kv-grow` | 9901 | 489.0 | 67.3 |

- **槽位三臂相同** => kv-grow 没有可回收的东西：我们 `kv_resident=0`，K/V 本来就不常驻 VRAM，而且 gfx906 构建根本没有 VMM（§2.3）。
- prompt_tps 三臂 487.9-489.1（±0.2%），**无差异**；A2/A1 的 RAM 占用从 45.9 GiB 涨到 63.4 GiB（46,989 到 64,968 MiB）（arena 37495 到 56762 MiB），属于去 resident 的纯代价。
- decode 中位 54.6 / 66.0 / 67.3 —— **这个量级是噪声，不是差异**（见 P88：同臂重复都在 54.6-67.3 之间摆）。
- **决定：采纳「去 `--resident-experts`」，kv-grow 弃用。** 依据见 §4.2 的三档复核（用户当场质疑"三臂差这么大为什么选最差的那个"，复核证明质疑正确：v1 的 A0 判断错了）。

### 4.1b 交错 A/B（每臂 2 轮 × 5 runs，greedy，M 档 21,827 token）

| 臂 | decode 逐次 | 中位 | 接受率 | prompt 中位 |
|---|---|---|---|---|
| A0 base | 46.4, 55.3, 57.6, 61.9, 62.8 / 46.2, 55.9, 61.2, 62.8, 61.7 | **61.2** | 95.8 / 95.9% | 488.2 |
| A2 nores | 54.9, 64.4, 67.6, 70.5, 68.9 / 54.4, 66.0, 67.0, 67.6, 65.7 | **67.6** | 96.4 / 95.8% | 488.8 |

混淆因子已排除：接受率差 <=0.6 点、prompt 相同；两轮交错方向一致，base 最低 46.2、nores 最低 54.4，分布几乎不重叠 => **+10.5% 是真实差异**。

### 4.1c 三档复核（采纳依据）

| 档 | base prompt / decode | nores prompt / decode | Δprompt | Δdecode |
|---|---|---|---|---|
| S (2,813 tok) | 408.8 / 62.6 | **429.5 / 70.0** | +5.1% | +11.8% |
| M (21,827 tok) | 488.2 / 61.2 | **488.8 / 67.6** | +0.1% | +10.5% |
| L (99,387 tok) | 464.9 / 33.8 | **468.1 / 42.6** | +0.7% | +26%（仅 32 token，分辨率低） |

机理：`--resident-experts` 把 36.93 GiB 专家副本 mlock 常驻（`generate.cpp:2482-2492`），占掉页缓存；去掉后专家落 page cache（RAM used 45.9 到 63.4 GiB（46,989 到 64,968 MiB）、MemAvailable 79.8 到 62.0 GiB（83,676,128 到 65,026,192 kB）），CPU 侧（`waitCPU` 4.01 ms/window）读专家更少打到磁盘。代价是 `arena_mib` 37495 到 56762（虚拟地址），冷读少 pinned 副本——但新版 0.1.49.2 上 S 档 prompt 反而 +5.1%，该代价已不成立。

### 4.2 为什么下一个是 Q2（路由 fp64）

1. **它是唯一"有确定对象"的源码项**：`router_top10.cu:220/225-226` 逐字 `s_ex[e] = exp((double) lv[j] - (double) mx)`、`for (e=0..n_expert) sum += s_ex[e]`、`const float inv = (float)(1.0 / s_sum)`；`:256-261` 归一化又跑一遍 double 累加。E=512 时每 token 每层 512 次 double exp + 512 次串行 double 加。
2. **它落在 7.0% 的桶里**（P87 的 `router+plan+bell` = 3.87 ms/window），同桶里 plan/bell 是纯调度、改不动，所以 router 是这个桶里唯一可下手的一段。
3. **改动小且可门控**：把 double 换 float 放在 `STRATA_ROUTER_F32=1` 后面，默认关；parity 测试 `router_top10_parity` 覆盖了 65,536 行（含 tie/near-tie/NaN/强制串行），能直接判"是否仍位等"。
4. **判据用分阶段值，不用 tok/s**：`STRATA_DECODE_TIMING=1` 下 `router+plan+bell` 的 ms/window 下降 >= 15%，且 `attention`/`VRAM hits` 等其它阶段不劣化（避免抢寄存器/改调度带来的副作用被掩盖）。

**已知风险**：位等（bit-identity）是它与 CPU 参考对齐的手段，换 float 后 parity 必失败；要么接受"非位等"（需要 needle/PPL 门），要么按 `router_top10_fast_kernel` 的"浮点树 + 单调区间回退"写法（`:267-281` 有完整论证：只在区间映射到同一 float 时用树，否则回退串行）。**采用后者。**

### 4.3 为什么 32.2% 的专家流没有配置杠杆

`VRAM hits 7.44 + waitB 6.49 + waitCPU 4.01` 是"专家没在显卡上"的代价，而显卡侧已经到顶：9901 槽 / 22.3 GiB（22,841 MiB）/ `vram_free 642`（贴着 768 的保留位）。加槽的三条路全部关闭：

- `--kv-grow`：gfx906 无 VMM（本节）
- `--expert-cache auto` 更多：已 auto 到顶，VMM 路径不可用
- 换更小量化：要压到 <= 22 GiB 相当于 2-bit，判据与风险都不成立（W776 §7 已列）

=> 这一块只能从 CPU 侧（`waitCPU`）与流式重叠下手，而 `--adapt-*` 已被校准器证明"默认最优"、AOV 实测无增益。所以它先挂起，等 Q2/Q3/Q4 有结果后再看。

---

## 5 编号映射（旧 -> 新）

| 旧 | 出处 | 新 |
|---|---|---|
| C1 合成车 / C2 三档基线 | §5 | 已完成（P26 改正、P62、P81） |
| C3-C8（pool-tasks、ple-inflight、host-core、aux-cpus、会话缓存、adapt） | §5 | 已关闭（P77/P80/P83/W781） |
| C9 kv-grow | §5 | **Q1** |
| C10 合规基线 | §5 | Q7 |
| D0 门禁 / E0 | §9/§10 | 已完成（P87） |
| D1-D4（DPP / fp64 gate / v_exp / readfirstlane） | §9 | **Q5** |
| E1 SH_STREAM | §10 | 已否决（P83） |
| E2 A1 / E4 v_exp | §10 | **Q5** |
| E3 溢出治理 | §10 | **撤销**（§2：跑着的内核无溢出） |
| E5 mmvq upstream | §10 | **Q4** |
| E7 路由 fp64 | §10 | **Q2** |
| E8 pcie 0.36 | §10 | 已否决 |
| F1（gr_down_v3/gr_up75 溢出） | §11 | **撤销**（§2） |
| F2 / F3 / F4 / F5 | §11 | **Q1 / Q2 / Q3 / Q4** |

---

## 6 纪律

1. 先量上限再动手：P87 那张表是天花板，改动不落在表上就不要改。
2. standalone 微基准赢不等于 serving 赢（routeK 三次、我方 `pool-tasks` 一次）。
3. 一次只动一面：配置与源码不混车；`kv-grow` 单独一趟。
4. 源码改动 env 门控、默认关；编译与调试只在 166；回滚位先确认。
5. **改之前先确认"这个内核真的在跑"**（AUDIT6 规则 B：符号在二进制 -> 在 dispatch 路径 -> 资源数 -> 才谈优化）。
6. **引用门必须引完整谓词**（AUDIT6 规则 A）：贴整条 `on = ...`，逐谓词标满足/不满足，再用引擎自己打印的 off 原因复核；
   本轮 `--kv-grow` 就是漏了 `vmm_available()`。
7. **decode 结论必须带混淆因子**（AUDIT6 规则 C）：接受率 + runs 数（>=10 或交错 A/B）；<5% 级只认 `STRATA_DECODE_TIMING` 的阶段 ms。
8. **单位写成"数值 + 单位 + 来源"**（AUDIT6 规则 D）：`/metrics` 的 `*_mib` 按 MiB，`/proc/meminfo` 是 kB，GiB 必须能回算。
9. **结论被推翻时，原文件加 banner**（AUDIT6 规则 E），不能只在新文档里写——W783/W784 已按此补勘误。
