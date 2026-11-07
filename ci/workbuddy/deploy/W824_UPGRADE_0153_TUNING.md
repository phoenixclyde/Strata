# W824 升级到 0.1.53 + 调优（2026-10-29 夜）

> 结论三句：
> 1. **已升到 0.1.53**（= tag v0.2.7.1），生产在跑，模型名同步改为 `qwen3.8-flash-next-ud-q4_k_xl-abliterated`，**无别名**。
> 2. **0.1.53 相对 0.1.49.2 无可测收益，但有"全部为正"的疑点**：prefill 三档 1453/2498/4568 是 **+9.1 / +0.8 / +3.3%**。
   ~~全在 4.4% 内（同二进制漂移带 4.6%）~~ —— **AUDIT11 更正**：那个 4.6% 是 1453 格的 A/A2 带，
   而在 **4568 格 A/A2 只差 0.1%**（8.26 vs 8.27），B53 的 +3.3% 超它 33 倍；1453 格 +9.1% 也超 2 倍。
   正确表述是「**三项全为正、且多数超出同长度地板，但未做 ABBA 配对，不能判为真回归**」。升级的理由是正确性修复，不是速度。
> 3. **调优这一轮全部否决**：`V2K` 配对后 0.0%、`spec-min-p 0.50` −14.5%；并且**发现 `ple` 相位已从 12.9-16.7% 掉到 0.5-0.9%**，P138/P141 那条线在新权重下已经不重要。

---

## 1 0.1.53 是怎么拿到的（下载被限速，用了文件级移植）

上游对 x86 Qwen 引擎在 0.2.7 → 0.2.7.1 之间的改动**只有 4 个参与编译的文件 + CMakeLists**：

| 文件 | 说明 |
|---|---|
| `CMakeLists.txt` | 版本号 0.1.52 → 0.1.53（+24/−2，其余是 Mac/DGX 打包） |
| `src/core/nv_defaults.cpp` + `include/strata/core/nv_defaults.hpp` | NVIDIA 默认值 |
| `src/kernels/cpu/portable.cpp` | ~~CPU 可移植内核~~ **我们根本不编它**：`portable.cpp:1` 逐字 `the CPU kernel symbols on a **non-x86** build (aarch64: DGX Spark / GB10, Grace)` |
| `src/prefill/moe_fused_iq.cu` | GB10/sm_121 的瓦片阈值（我们不受影响） |

其余 26 个引擎文件全是 `src/dsv41/*`（DeepSeek 引擎，我们 `-DSTRATA_BUILD_DSV41=OFF`）与 `metal/*`（Linux 不编）。

> **AUDIT11 修正"变更面"的口径**：上面 4 个文件里，`portable.cpp` 只在 **non-x86** 构建里替代 AVX 内核，
> `nv_defaults.*` 是 **NVIDIA** 默认值，`moe_fused_iq.cu` 是 **sm_121（GB10）** 的瓦片阈值。
> ⇒ 对**本机 x86_64 + gfx906** 的实质变更 ≈ **只有 CMakeLists 的版本号**。
> 这也解释了为什么 A/B 三档"全为正但幅度小"：**本来就不该有效益**。原文"4 个参与编译的文件"技术上不算错（它们确实进编译单元），
> 但会让读者以为升级带来了实质代码变化。
codeload 限速到 10-21 KB/s，所以先用 `cp -al` 建树失败（`fs.protected_hardlinks=1` 拒绝 root 文件），
改用 tar 管道只复制源码（258 MB / 7973 文件 / 1.9 s），再覆盖上述 5 个文件、重打我们的 3 处补丁。

**补丁复用的两个坑**：
- `set(_strata_gpu_include_directories …)` 在 0.2.7.1 里出现 **3 次**（0.2.7 是 2 次）⇒ 必须靠 `Strata: HIP (gfx906 compat) enabled` 定位分支，不能用行内容。
- `qsa_decode_attn.cu` 从 0.2.7 树复制过来时**已经是 W794 版本**，补丁脚本的自检 `base.count("attn_chunk_kernel<3")==0` 因此报错 —— 这是正确行为（cmp 逐字节相同，跳过 D 步）。

构建：与生产**逐项相同**的 CMake 选项，`nice -n 15 ninja -j 10`，**164/164，rc=0，约 4 分钟**，产物 38,237,344 B，`--version` = `strata 0.1.53`。
核验：`rocBLAS tuning enabled`（W793 生效）、`STRATA_MMQ_KQ`、`STRATA_PLE_AUTO_RAM`、`STRATA_EXPERT_V2K`、gfx906 代码对象 **140**、`--help` **139 个 flag（与 0.1.49.2 相同，零参数变化）**。

## 2 A/B：0.1.53 与 0.1.49.2 无可测差异

三臂交错 A(0.1.49.2) → B53(0.1.53) → A2(0.1.49.2)，同一语料（`sha16` 逐条相同），暖缓存，不清 page cache。

**prefill（wall，秒）**

| tokens | A | B53 | A2 | B53 相对 A/A2 带 |
|---:|---:|---:|---:|---|
| 1453 | 3.73 | 4.07 | 3.90 | 带外 +4.4% |
| 2498 | 5.27 | 5.31 | 5.26 | 带外 +0.8% |
| 4568 | 8.26 | 8.53 | 8.27 | 带外 +3.1% |

同二进制 A vs A2 的带宽本身是 **4.6%**（3.73 vs 3.90）⇒ B53 的 0.8-4.4% **落在噪声带内**，判"无差异"。
启动 199 / 240 / 231 s，无差异。

**解码：这一轮不可用**，A 39.4 / B53 38.7 / A2 **45.8** —— 同二进制差 **16%**。原因见 §4。

## 3 调优：三个候选全部否决（含一个被配对实验推翻的假信号）

| 臂 | 改动 | 解码中位 | prefill 4563 tok (GPU timeline) | 判定 |
|---|---|---:|---:|---|
| N0 | 0.1.53 基线（22:50） | 41.8 | 7055 ms | — |
| T1 | `STRATA_EXPERT_V2K=1` | **45.0** | 7060 ms | 初看 +7.7% |
| N0b | 基线重跑（23:15） | **46.9** | 7029 ms | 同配置比 N0 高 **12%** |
| T1b | `V2K=1` 配对重跑 | **46.9** | 7040 ms | **0.0%** ⇒ 假信号 |
| T2b | `--spec-min-p 0.50` | **40.1** | 7037 ms | **−14.5%** ⇒ 否决 |

- **`STRATA_EXPERT_V2K`（Q4_K 的 V2K 解码内核）**：机制上完全对口（`gu_type=12 / d_type=7 / n_embd=2560 / n_ff=640`，
  gfx906 不在默认开启的 `#if defined(__HIPCC__) && !defined(STRATA_HIP_GFX906)` 分支里，必须显式 =1），
  且上游称与旧内核**逐位相同**。但配对实验是 **45.0 → 46.9 与 46.9 打平**，初次的 +7.7% 是容器漂移。
  **不采纳**（保留为"等 ABBA 实验再判"的候选，因为它没有质量风险）。
- **`--spec-min-p 0.50`**（上游 setup 值，我们配 0.70）：解码 **−14.5%**。方向明确——**把窗口延长得更积极，在这台机上更亏**。
  ⇒ 反过来值得试 `0.85`（更保守、窗口更小），这是下一轮唯一有先验的方向。
- **prefill 对三者完全无反应**（7029-7060 ms，差 0.4%）——符合机制：V2K 与 spec-min-p 都只作用于解码路径。

## 4 一个必须先承认的方法学问题：跨容器比解码无效

同一份配置、同一晚、只隔 25 分钟：N0 41.8 → N0b 46.9（**+12%**）；更早的 A 39.4 vs A2 45.8（**+16%**）。
逐臂看，解码在**同一次请求序列内**单调上升（p0 最低、p3/p4 最高），跨臂则随夜深持续变快 ⇒ 预热/时钟/页缓存状态的叠加，
不是二进制差异。**结论：本机上"换配置比解码"必须 ABBA 交错 + 取同阶段样本，否则 ±12-16% 的假信号随时出现。**
（这也解释了 W820 那轮"同二进制差 38%"。）

本轮 prefill 用的是**引擎自己的 GPU timeline 相位表**（`STRATA_PREFILL_TIMING=1`，五臂都开了），
同一请求的相位分解可复现到 0.5% 以内，是目前唯一能判 2-3% 的标尺。

## 5 最重要的发现：`ple` 不再是瓶颈（推翻 W810 的 12.9-16.7%）

同一台机、同一张表、4563 token 的相位分解（0.1.53）：

| 相位 | ms | 占比 |
|---|---:|---:|
| **gate/up** | 1533 | **21.8%** |
| **attn** | 1091 | **15.5%** |
| **gemm down** | 988 | **14.1%** |
| gdn | 800 | 11.4% |
| qsa proj | 608 | 8.7% |
| hc read | 585 | 8.3% |
| recurrence / router+shared / write | 256 / 192 / 86 | 3.6% / 2.7% / 1.2% |
| **ple** | **34-42** | **0.5-0.9%** |

W810 在 **UD-IQ4_XS** 上测到 `ple` 占 **12.9-16.7%**；换到 **UD-Q4_K_XL** 后只有 **0.5-0.9%**（五臂一致）。

**机理（推测，未单独验证）**：PLE 表 26.8 GiB 现在整张留在页缓存里（`Cached` 52 GB），`ple` 相位不再等盘；
而 W810 当时 ComfyUI 占 52 GB、表被竞技场的 55.43 GiB 缓冲流冲掉，才出现 250 ms/1k 的等盘。
⇒ **P138/P141（`--ple-io ram` / 行缓存 / 小 chunk 藏 PLE）这条线在新权重上已经不重要**，
    真正该花时间的是 **gate/up + down（36%）与 attn（15.5%）**。

**这条要写清边界**：`ple` 小 ≠ PLE 免费。`host: chunk setup (PLE rows …)` 仍有 **80-138 ms**（主机侧），
而且页缓存一旦被挤掉就会回到 W810 的形态。它现在"不重要"是**这台机当前内存状态的结果**，不是结构性的。

## 6 状态

- 生产：`exe=/data/bin/strata-0.1.53`，33 args / 13 env，`--pack /data/packs/ud-q4_k_xl`，
  `STRATA_MMQ_KQ=1`、`RT_SKIP=7`、`spec-min-p 0.70`、`pcie-frac 0.20`，槽位 **7551 / 22.04 GiB**，余量 660 MiB。
- 模型名：`qwen3.8-flash-next-ud-q4_k_xl-abliterated`，**`aliases` 已删除**（按机主要求）。
  兼容性事实：`/v1/chat/completions` **不校验** model 名（只有 `/v1/load`、`/v1/unload`、`/props` 会 404）
  ⇒ 旧名客户端聊天不受影响，走 `/props` 的工具需要改填新名。
- 回滚：`data/w824_pre_promote.json` 把 `exe` 改回 `/src/build-906/strata` 即可（旧二进制仍在镜像里）。

## 7 下一轮该做什么（按证据强度排序）

1. **`--spec-min-p 0.85`**：0.50 明确亏损（−14.5%）⇒ 沿反方向试探一次。
2. **ABBA 交错重测 `V2K`**（N0→T1→T1→N0），每格 ≥5 次、取 p3/p4 同阶段样本；它无质量风险，只差证据。
3. **`attn`（15.5%）与 `gate/up`（21.8%）** 才是新权重的主战场：前者有 `STRATA_GFX906_ATTN_*` 两个未开开关，
   后者与 `MMQ_KQ` 已开、但 `STRATA_DENSE_MMQ` 未验。
4. PLE 那四条（P138/P139/P140/P142）**在新权重下重新定级为"低优先"**，除非页缓存被挤。

## 8 数据与脚本

- `albus/w824/{patch_0271.py,w824_build.sh,w824_arm.sh,w824_ab.sh,mkarm2.py,mkarm3.py,mkarm4.py,promote_153.py,analyze.py,drop_alias.py}`
- 原始：`data/w824_{A,B53,A2,N0,T1,N0b,T1b,T2b}.json`、`data/w824_*.log`、`data/w824_ab.log`
- 源码包：`albus/w824/strata-0.2.7.1.tar.gz`（31,344,359 B，5805 成员）

---

## 9 第二轮（10-29 23:38 → 10-30 00:10）：`ATTN_REDUCE12` 拿到 −3.8%，已采纳

### 9.1 先排掉两个候选（零成本）

- **`STRATA_DENSE_MMQ=1`：gfx906 上结构性不可用。** `prefill/gemm.cu:1205` 的 `native_mmq()` 整个函数在
  `#if defined(STRATA_PREFILL_MMQ) && defined(__HIPCC__)` 内；CMake 是 `option(STRATA_PREFILL_MMQ … OFF)`，
  只有 ON 才 `target_compile_definitions(... STRATA_PREFILL_MMQ=1)`；而
  `if(STRATA_PREFILL_MMQ AND NOT STRATA_ENABLE_HIP) FATAL_ERROR`，同时 `STRATA_HIP_GFX906` **拒绝** `STRATA_ENABLE_HIP`。
- **`STRATA_EXPERT_V2K=1`：第三次无差异**（见 §3 + 本轮 V1 臂 45.1 vs 45.9/44.5）。定案不采纳。

### 9.2 `STRATA_GFX906_ATTN_REDUCE12=1`：两对独立配对，重复性 0.1%

> **AUDIT11 更正措辞**：这里说的"重复性 0.1%"是**跨容器实例**的（`w824_arm.sh:18,21` 每臂都 `rm -f` 后 `docker run`，
> N1 / N1b 是两个实例），不是"同容器内"。能稳到 0.1% 的原因是**用的是 GPU 事件计时的相位表**，
> 而 decode 的 tok/s 走 wall、受 host 影响，同一批臂里就漂 12-16% —— 两者不矛盾，但措辞必须分清，否则会有人把 0.1% 套到 decode 上。

| 指标（4563 token） | N1 | N1b | A1 | A1b | 结论 |
|---|---:|---:|---:|---:|---|
| prefill GPU timeline | 7034 ms | 7027 ms | **6765** | **6757** | **−3.8%** |
| 其中 `qsa attn` | 1089 | 1091 | **810** | **811** | **−25.6%** |
| gate/up | 1534 | — | 1538 | — | 不变 |
| gemm down | 988 | 986 | 992 | 989 | 不变 |
| gdn / hc read / dequant / ple | 801 / 586 / 611 / 37 | — | 801 / 586 / 613 / 32 | — | 不变 |
| wall 1453 / 2498 / 4568 | 3.34 / 4.66 / 7.73 | 3.37 / 4.64 / 7.73 | **3.28 / 4.53 / 7.45** | **3.32 / 4.53 / 7.44** | −1.5 / −2.6 / −3.7% |

- **跨容器实例的重复性 0.1%**（N1 7034 vs N1b 7027；A1 6765 vs A1b 6757），相位归因精确到 2 ms。
  我把 20 个相位逐项加总核对：N1 合计 **7033** vs total **7034**（差 1 ms）、A1 合计 **6765** vs total **6765**（**精确闭合**），
  `qsa attn −279 ms` + 其余净 +11 ms = **−268 ≈ −269 ms** ⇒ 归因链条完整（AUDIT11 复算）。
- 解码**不变**：tok/s 45.9/44.5 → 45.8/45.3；`ms/window` 38.2/37.7 → 36.9/36.7，但 `tokens/window` 也降（1.79/1.66 → 1.65/1.64），
  净持平 ⇒ 收益只在 prefill。
- 生产冒烟（新容器、无 TIMING）：4568 token **7.07 s**（受控基线 7.73 s；含容器漂移，不作为判据）。

**为什么现在才发现**：它在 gfx906 里是 **opt-in 且默认关**（`AMD_HIP.md`：「The attention switches
`STRATA_GFX906_ATTN_QUERY_SWIZZLE=1` and `STRATA_GFX906_ATTN_REDUCE12=1` are off by default and compiled only into
this build」），而它同时作用于 prefill / verification / MTP —— 我们一直只开了 swizzle 那个。

**质量边界必须写明**：它换的是归约顺序（`attn_chunk_kernel<3,false,true,true>` vs `<3,false,true>`），
**不保证逐位等价**。上游对 gfx906 其他开关写的是"checked bitwise"，对这个没有这句话。
⇒ 已采纳（收益 3.8% 且机制定位精确），但**下一步必须量 teacher-forced KL**；回滚就是删掉这个 env。

### 9.3 本轮新增的两条方法学

1. **解码要用 `STRATA_DECODE_TIMING=1` 的分解**，不要只看 tok/s：
   真实请求是 `64-74 windows、2.9-5.9 ms draft、1.65-2.10 tokens/window、草稿接受 57-61/76-99（75-77%）`，
   tok/s 由 `tokens/window ÷ ms/window` 合成，**接受率一变 tok/s 就变**，所以判内核必须比 `ms/window` 与 `verify` 分量。
   （另外：`mt_read` 的纯 prefill 请求会打出 `1 window / 1.00 tokens/window / draft 0.00` 的行，**别把它当解码样本**。）
2. **驱动脚本必须互斥**：本轮我犯了错——上一轮驱动还在跑 V1 时就起了新驱动，两者用同一个容器名
   `w824arm`，后起的 `docker rm -f` 把前一个的容器删了（V1 因此丢了读长 JSON）。
   已在 `w824_ab.sh` 加护栏：检测到另一个 `w824_ab.sh` 就 `exit 4`。
   要中止旧驱动请用 `kill -9`（`SIGTERM` 会触发它自己的 trap 去 `docker start` 生产，反而撞车）。

### 9.4 生产现状（10-30 00:10）

`exe=/data/bin/strata-0.1.53`、`--pack /data/packs/ud-q4_k_xl`、`STRATA_MMQ_KQ=1`、**`STRATA_GFX906_ATTN_REDUCE12=1`（新）**、
`RT_SKIP=7`、`spec-min-p 0.70`、`pcie-frac 0.20`，env **14 项**（相位表两个 env 已撤），HEALTHY。

---

## 10 质量门：`ATTN_REDUCE12` 逐位等价（底噪先被压到 0）

### 10.1 第一轮 KL 判不了——因为底噪比效应还大

用现成链路（`STRATA_LOGPOS` + `STRATA_LOGPOS_TOPK=64` 写逐位置表 → `mt_kl.py` 跑脚本化对话 → `kl_prop` 口径算配对 KL），
每臂 60 个 scored 位置（pos 239..5463）：

| 配对 | 均值 KL | 中位 KL | argmax 同 | top-10 重叠 | PPL |
|---|---:|---:|---:|---:|---:|
| Q1 ‖ Q1b（**同配置**） | 0.0253 | 0.0000 | 98.3% | 0.84 | 5.05 vs **4.37** |
| Q1 ‖ Q0（开 vs 关） | 0.0459 | 0.0000 | 98.3% | 0.83 | 5.05 vs 5.25 |
| Q1b ‖ Q0 | 0.0262 | 0.0001 | 100.0% | 0.80 | 4.37 vs 5.25 |

**同配置两次的 PPL 差 15%、只有 16.7% 的位置逐位相同、p95 |Δlp| 2.40 nats** ⇒ 这个尺子当场失效。
根因不是 reduce12，是 **`STRATA_PREFILL_CPU_SHARE=auto`**（W803 早就写过：share 让 prefill 逐次不同；share=0 时两遍 md5 相同）。

### 10.2 第二轮：把 share 固定为 0，三份文件同哈希

K1（reduce12=1）/ K0（=0）/ K1b（=1 重跑），全部 `STRATA_PREFILL_CPU_SHARE=0` + LOGPOS：

```
md5  38fa1653c08dba8eb7fb41f9be535674  w803_logpos_K0.tsv     (66,045 B)
md5  38fa1653c08dba8eb7fb41f9be535674  w803_logpos_K1b.tsv    (66,045 B)
md5  38fa1653c08dba8eb7fb41f9be535674  w803_logpos_K1.tsv     (66,045 B)
```

配对 KL 三对全 **0.0000**，argmax 一致率 **100%**，top-10 重叠 **1.00**，mean|Δlp_tgt| **0.0000**。

⇒ 两条结论：
1. **底噪 = 0**（同配置两次逐字节相同），这把尺子在 `share=0` 下是可用的；
2. **`ATTN_REDUCE12` 在受评路径上逐位等价** —— 它只换了归约的分块方式，算术结果不变。
   §9.2 里"质量未验"这条**已关闭**，−3.8% 的 prefill 收益可以放心留。

**边界**：这 60 个位置是 verify 窗口的 teacher-forced 读，prefill 自身的数值没有被直接打分；
但同一内核只换模板参数、验证路径逐位相同，可认为不引入数值偏差。

### 10.3 一条能复用的流程（写进规矩）

> 本机做任何 teacher-forced 质量门，**必须先把 `STRATA_PREFILL_CPU_SHARE` 固定（=0）**，
> 否则噪声（0.03 量级）与要判的效应（0.03 量级）同量级，结论只能是"判不了"。
> share 是 prefill 的速度特性，只在量质量时改；生产仍是 `auto`。

顺带解释了一个老现象：**教师强制的 logprob 在 `share=0` 下完全可复现，而贪心生成仍不可复现**（W816/W819）
⇒ 数值链路是确定的，贪心分岔来自别处（窗口批形状/接受路径），不在算子本身。

### 10.4 生产状态（10-30 01:35）

`exe=/data/bin/strata-0.1.53`、`--pack ud-q4_k_xl`、`MMQ_KQ=1`、`ATTN_REDUCE12=1`（**已验逐位等价**）、
`RT_SKIP=7`、`spec-min-p 0.70`、`pcie-frac 0.20`、`share=auto`，env 14 项，无 LOGPOS/TIMING 残留。
