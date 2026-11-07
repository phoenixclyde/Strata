# W892 · 外部证据交叉核对：**v_dot8 不是我们的杠杆，「内存并行度」才是** —— 而我们生产还跑着旧的专家内核

**来源**：一条分享出来的对话（4×4090 / MI50 那次），加上我自己按它给的线索去核的原始资料。
**结论三句**：

1. 那条对话的头号建议（「改用 `v_dot8_i32_i4`，decode 1.5–2.5×」）**被它自己引用的资料否掉了**——
   hipfire 的 MI50 实测 PMC 是 **VALUBusy 26–41%、内存才是限制项**，ALU 不是墙。
2. 真正被两边证据同时指向的杠杆是**内存并行度**（每 workgroup 多行 / 半波拆分 / 无 LDS 暂存 / Y-tile 预取）。
3. **我们生产跑的是旧的专家内核**：`s27`（4 rows per warp + 激活进 LDS，即上面那套做法）由 `STRATA_EXPERT_V2K` 控制，
   **在 gfx906 上默认关、上游明说「未在其他卡上测过」**。这是零代码、一次重启就能验的。

---

## 1 那条对话里，哪些能用、哪些不能用（逐条核过）

| 它的说法 | 核查结果 |
|---|---|
| 「gfx906 每个 warp 每周期只有 1 个 dp4a 发射端口，VALUBusy 卡死在 ~48%，是硬件发射率墙」 | **半对**。dp4a 确有发射率上限（`wiki-gfx906` 把它列为已知 ISA 特性），但 hipfire 在 MI50 上实测 decode 的 PMC 是 **VALUBusy 26–41%**，`MemUnitStalled` 0.95–4.23（>4% 已属显著）⇒ **限制项是内存，不是 ALU**。「48% 卡死」这个数**在它引用的文档里找不到** |
| 「改用 `v_dot8_i32_i4`（int4×int8）能把 dp4a 条数减半 ⇒ decode 45→70–110」 | **指令事实对，推论错**。`v_dot8_i32_i4` 在 gfx906 上确实存在且实测 **43.5–44.4 TOPS vs sdot4 21.7–22.3（2.0×）**；但既然 ALU 只忙 26–41%，把 ALU 提速一倍**不会**变成 1.5–2.5× 的端到端收益。它最多把「撞 ALU」的那部分削掉 |
| 「Strata 没有 gfx906 专用内核，全靠 llama.cpp 的 ggml MMQ」 | **对我们的 fork 是错的**。我们有 `native_mmvq`（llama.cpp 血统，但含本仓的 wave-rows 实测表）、`qsa_prompt_attn`、`s26/s27` 专家内核、以及 gfx906 的 arch 默认表（`W839`：上游把 `apply_arch_defaults` 放进 `#if STRATA_USE_HIP`，我们补了 gfx906 分支）。「MMQ 血统」对，「没有专用内核」错 |
| 「锁频 `--setperfdeterminism` 能消掉功率摆动，tok/s +5–15%」 | **实测否掉**：decode 期间 sclk 已经钉在 **1725 MHz 最高档**，功率 114–220 W 是同一时钟下的工作量波动，不是变频；卡也没撞 300 W 功耗墙 |
| 「memory 和缓存命中比显卡型号更重要」 | **与我们自己的数据一致**：专家命中 98.9%、PCIe 0.00，瓶颈全在 HBM 有效带宽 |

## 2 外部实测（原文数字）

**① `wiki-gfx906`（用 `llvm-mc -mcpu=gfx906` 逐条验证 + 4 张 MI50 实测）**

| 指令 | gfx906 | 实测 TOPS（依赖链 / ILP4） |
|---|---|---|
| `v_dot4_i32_i8`（sdot4, int8×4） | ✅ | 21.7–22.3 / 43.0–44.4 |
| **`v_dot8_i32_i4`（sdot8, int4×8）** | ✅ | **43.5–44.4 / 85.3–86.2** |
| `v_dot4c/dot8c` | ❌ 不支持 | — |
| `v_pk_fma_f16`（packed fp16） | ✅ | — |

⇒ 我们仓里 **只有 sdot4**（`__builtin_amdgcn_sdot4` ×1、`dp4a` 出现 223 处、`v_dot4_i32_i8` 提及 1 处），**没有 sdot8**。
但按 §1 的推论，**这不是当前的瓶颈**。

**② hipfire `2026-05-05-gfx906-decode-investigation.md`（MI50 / Qwen3.5 9B / Q4_K_M / batch=1）**

| 实现 | tg128 tok/s | ms/token | 有效带宽 |
|---|---:|---:|---:|
| stock llama.cpp | **61.55** | 16.2 | ~305 GiB/s（≈328 GB/s） |
| skyne98 fork | 63.48 | 15.7 | ~315 GiB/s |
| hipfire MQ4 | 50.7 | 19.7 | ~250 GiB/s |

原文诊断：**"Decode is HBM-bound but not saturated"（约 25% 峰值）**，
PMC：`VALUBusy 26–41%`、`MemUnitStalled 0.95–4.23`；
三个具体手法：**① 一个 wave64 干两行输出（half-wave split，`lane_id/32`），把每 CU 的访存并行度翻倍；
② 完全不搭 LDS（HBM→寄存器→dp4a）；③ Y-tile 预取（inline asm `global_load_dword`，软件流水）**。

## 3 我们自己的数，正好落在同一张图上

| 我们实测 | 值 | 对照 |
|---|---:|---|
| 专家读有效带宽（`W891` 现算） | **411 GB/s** | = 884 的 **46.4%**；hipfire 说 llama.cpp 是「~25% 峰值且未饱和」——同一族现象 |
| 我们探针里 R（每块行数）1→2 | **1.84×**（`W862 §3.3`，qkv 27.85 MB） | 与 hipfire 的「一行变两行」同源 |
| 生产窗口里专家读占比 | 11.58 / 44.4 = **26.1%** | 专家读是单项最大块 |
| 专家命中 / PCIe | 98.9% / **0.00** | 不是驻留问题 |

⇒ **「多行共享一个权重块」这条在我们仓里已经被证明有效（1.84×），但只落到了 `native_mmvq` 的普通矩阵乘上。**
生产的专家路径走的是 `native_expert_grouped` → **旧内核**。

## 4 发现的零代码杠杆：`STRATA_EXPERT_V2K`

`native_expert_grouped`（`iq_kernels.cu:6246`）里，`s27` 新路径的开关是 `STRATA_EXPERT_V2K`：

```cpp
// stream B: UD-Q4_K_XL's Q4_K / Q5_K gate/up and Q5_1 / Q8_0 down (see S27 below)
// MODEL-UPDATE: on by default on gfx12 …; STRATA_EXPERT_V2K=0 turns it off, =1 turns it on
// elsewhere (not measured on other cards)
static const bool v2k = [] { … #if defined(__HIPCC__) && !defined(STRATA_HIP_GFX906) … gfx12 … #else return false; #endif }();
```

| 事实 | 值 |
|---|---|
| 我们的卡 | `STRATA_HIP_GFX906` ⇒ 编译期直接 `return false` ⇒ **生产 v2k = 关** |
| 守卫形态 | `gu_type==12|13`（Q4_K/Q5_K）+ `d_type==7|8`（Q5_1/Q8_0）+ **n_embd 2560 / n_ff 640** |
| 注释逐字 | *"UD-Q4_K_XL's Q4_K / Q5_K gate/up and Q5_1 / Q8_0 down"* ⇒ **就是我们的模型** |
| s27 的做法 | *"the gate/up of the V2K path (**4 rows per warp**, the chunk's activations **in LDS**)"* ⇒ **正是 §2 那套「多行 + 暂存」** |
| 二进制里有没有 | **有**（`strings` 命中 `STRATA_EXPERT_V2K` 与 `STRATA_EXPERT_V2`） |
| 改不改比特 | 源码注释：gfx12 上 *"every output the old kernels' bits"*（逐位相同）⇒ 若在 gfx906 也成立，**不需要 KL 门**，只需逐字比对 |

**这就是本轮最值钱的一条**：上游在 gfx12 上默认开、并标注「bitwise」，而 gfx906 **默认关、且明写未测**。
我们的形状、我们的量化格式正好在守卫里。

## 5 优化后的队列（只增两条，砍一条）

| 序 | 条目 | 做什么 | 判据 | 成本 |
|---|---|---|---|---|
| **新1** | **R47 `STRATA_EXPERT_V2K=1`** | 一次重启，只加一个 env | 专家读 **11.58 → ≤9.0 ms/窗口**（≥530 GB/s）；**同 prompt 贪心输出逐字相同**；窗口 ≤42 ms | 零代码 + 1 次重启 |
| ~~新2~~ **已否** | ~~**R48 锁频 A/B**~~ | **当场测完，无空间**：decode 期间 sclk 全程 **1725 MHz（最高档 level 8）**，功率 114–220 W（TDP 300，未撞 cap），请求结束才掉到 925 MHz/17 W ⇒ **没有 DVFS 抖动可锁** | 判据不成立 | 0（已用 8 秒采样证否） |
| ~~砍~~ | ~~v_dot8 / sdot8 改造~~ | — | **证否**：ALU 只忙 26–41%（hipfire PMC）⇒ 加 ALU 不是端到端杠杆 | 省掉一次内核工程 |
| 保持 | R44 证据链（INFLIGHT）/ R46 prompt attn / R36 / R30' | 不变 | — | — |

**R47 的风险与处置**：
- 若 `s27` 在 gfx906 上不逐位相同 ⇒ 需 KL 门（`STRATA_LOGPOS`，底噪 0.0024），成本 +1 次重启；
- 若 `d_type` 实测不是 7/8（例如某些层是 Q6_K）⇒ 守卫不成立，整层回落到旧内核；**用启动日志确认实际走哪条**；
- 回滚：删 env + 重启（配置已备份，`bak_w890_*`）。

## 6 复算 / 验证命令

```bash
# ① 确认 v2k 是否生效（重启后）
docker exec strata166-407 bash -lc 'grep -ai "v2k\|native_expert_grouped" /data/strata-huihui-ud-iq4_xs.log | tail -3'
# ② 专家读现状（现算，不要手抄）
python3 ~/strata166/ci/derived_check.py
# ③ 时钟/功率是否在摆（decode 期间采样）
for i in $(seq 1 20); do rocm-smi --showclocks --showpower | grep -E "sclk|Power"; sleep 1; done
# ④ 逐字比对（R47 是否改答案）
python3 ~/strata166/ci/decode_timing_probe.py --prompt 600 --max 128   # 保存输出文本，两臂对比
```

## 7 一条方法学（这轮真正的教训）

那条分享对话的**结构**是对的（先定性瓶颈、再找指令级杠杆），但**结论反了**：它把「指令存在且更快」当成了「端到端会更快」，
跳过了「ALU 到底忙不忙」这一步。而 hipfire 的 PMC 一行就把这一步补上了。
⇒ 我们的规矩再加一条：**任何"换指令/换精度能 X 倍"的建议，先问"那个单元现在忙多少"**——
我们自己的 `W887`（prompt attn 只跑到 FP32 峰 11–16%）其实就是同一个教训。
