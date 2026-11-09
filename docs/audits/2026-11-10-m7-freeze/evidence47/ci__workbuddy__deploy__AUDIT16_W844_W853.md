# AUDIT16 · 审计 W844–W853（10 轮 / 12 件）

> VERDICT: AUDIT16 P0=4 P1=9 P2=10 P3=3 src=AUDIT_INDEX:16（AUDIT28 回填，不新增结论）


> **总判：P0 4（**其中 P0-4 于 2026-11-01 00:4x 自行撤回**，见 §1-P0-4 顶部）/ P1 9 / P2 10 / P3 3 = 26 条**
>
> ⚠️ **撤回记录**：P0-4「MMQ 从未编进生产线」**是错的**。证据在 `gfx029-build/build.ninja` 里：
> `strata_prefill` 的编译行带 `-DSTRATA_PREFILL_MMQ=1`（来自 `CMakeLists.txt:2317` 的 `STRATA_ENABLE_CUDA` 分支，
> 而 `STRATA_HIP_GFX906` 在 `:91-93` 强制打开 `STRATA_ENABLE_CUDA`）。**CMake 选项** `STRATA_PREFILL_MMQ=OFF`
> 只决定"没有 CUDA 分支时走哪条备用构建路径"（`:2392` 的 `elseif`），与"运行期有没有 MMQ"是两件事。
> 我把选项当成了定义，且把「`MMQ tile` 日志缺失」当证据——那条打印只存在于 W795 的 p4/p5 补丁镜像里，
> 当前树根本没有这条打印，缺失不构成证据。**教训写进 §11。**，另有 4 条"上网核实通过、不必改"。
> 范围由 `albus/w831/audit12_scope.py` 机械定出（W844–W853 全文提及数全为 0，W843 及以前已被
> AUDIT14/15 覆盖）——不靠记忆往前推。
> 日期 2026-10-31 23:5x–次日 00:3x。**本轮审计不动生产进程**（生产实况另见 §7）。
>
> 先说三条最重要的：
> 1. **W853 的相位表整表取自"重启后第 2 个 warm 请求"**（rep0 的实测行另有三条，没被用）；
>    报告写"各 3 次"实际每档只测了 1 次。数字与结论要按 rep0 重列（§1-P0-1）。
> 2. **W853 的两条机理归因都读错了源码**：`prefill.cpp:3456` 描述的是"已由 issuer 线程消除的旧等待"，
>    而 `gemm_iq_f16_grouped` 在 `__HIPCC__` 下**恒不可达**、且只处理 IQ 格式（§1-P0-2/P0-3）。
> 3. ~~**账本说 MMQ 已采纳，二进制说 MMQ 从未编进去**~~ **【已撤回 · 2026-11-01 00:4x】**
>    ~~P112 记 `REJECTED(value=0)`=保留 MMQ，但 12 个历史构建 cache 全是 `STRATA_PREFILL_MMQ=OFF`，
>    `mmq::built()` 是桩 false，近三次启动 0 条 MMQ 派发行。这条是所有轮次里最大的结构性发现。~~
>    **真相相反**：`gfx029-build/build.ninja` 里一直是 `-DSTRATA_PREFILL_MMQ=1`，**MMQ 编着且默认开**；
>    当时拿来看「编没编进去」的那个 cache/桩判断读错了目标文件。**留下的真问题**见 `R17`
>    （MMQ / fused / FP16 各几层、`dequant` 相位语义）——那个才是还需要查的。
>    **AUDIT22 注**：本条摘要此前一直没跟正文的撤回同步（正文 §1-P0-4 早就划掉了），
>    这正是「撤回只回写一处」的典型；现已同步。

---

## 0 判法（这轮怎么审的）

| 维度 | 做法 | 产出 |
|---|---|---|
| 数据可复现 | 每份 A/B 都回原始 `data/w85*.txt` 与 `*.json` 逐行对照，不读报告表 | §1-P0-1、P1-5/6/7 |
| 机理 | 引用到的每个 `file:line` 都打开读上下文，并查调用者/编译门 | §1-P0-2/3/4 |
| 生产实况 | 容器/镜像/ROCm/表/`/src`/门禁/TIP 全部现取 | §7 |
| 上网 | 12 条外部断言逐条查（官方矩阵、release notes、两个上游 PR、社区仓、打包邮件列表） | §5 |
| 账本 | `PROGRESS.tsv` / `PARAM_REGISTER.tsv` / 方案 / `SESSION_STATE` 四处交叉 | §2-P1-10/11/12 |

---

## 1 P0（会让人做错决定，或数据不可复现）

### P0-1 W853 相位表整表来自 warm 请求，且"各 3 次"不成立

**证据**（`data/w853_m5_233726.txt`，9 条 timing 行 + 3 条 `READ strata`）：

| 档 | 客户端 warm0/warm1/rep0（s） | 引擎 timing 墙钟（ms） | 归属 |
|---|---|---|---|
| 300 | 1.76 / 1.55 / 1.44 | 1416 / 1184 / 1084 | 277 / **280** / 248 tok |
| 1300 | 2.60 / 3.09 / 2.85 | 2230 / 2694 / 2453 | 946 / **1239** / 1162 tok |
| 2575 | 4.15 / 4.35 / 3.76 | 3687 / **3863** / 3312 | 2088 / **2323** / 1914 tok |

报告 §2 的三行（277 / 1239 / 2323 tok）**全部是 warm1**，而 rep0（248 / 1162 / 1914）从未出现在报告里；
且"277 tok"这一行把 warm0 的 token 数贴到 warm1 的计时上。报告 §0 写"三档 prompt 各 3 次"——
脚本 `m5.sh` 只发 `reps=1`，日志里每档只有一条 `rep0`。

**为什么这很严重**：`SESSION_STATE §4` 与 `PROGRESS M5` 都记着"重启丢前 2 个请求"。
同一现象在 W844 的 warm0 上是 6.00 s vs 实测 4.55 s（+32%）。用一个已知异常的样本集做相位归因，
等于把冷启动成本当成稳态结构。

**重列（rep0，n=1/档）**：

| 相位 | 248 tok | 1162 tok | 1914 tok |
|---|---:|---:|---:|
| gemm gate/up | 204 (18.9%) | 524 (21.5%) | 735 (22.2%) |
| gemm down | 143 (13.3%) | 335 (13.7%) | 462 (13.9%) |
| dequant | **216 (20.0%)** | 289 (11.8%) | 315 (9.5%) |
| wait copy | **137 (12.7%)** | 290 (11.9%) | 293 (8.9%) |
| gdn | 67 (6.2%) | 219 (9.0%) | 319 (9.6%) |
| qsa attn | 9 (0.9%) | 95 (3.9%) | 222 (6.7%) |
| host staging | 92 ms | 369 ms | 565 ms |
| GPU / wall | 1081 / 1084 | 2442 / 2453 | 3312 / 3328 |

**结论变化**：
- "dequant 与 wait copy 都是固定成本"**只对 dequant 成立**（216→289→315，7.7× token 只涨 1.46×）；
  **wait copy 不是**：137→290→293，2.1× 后饱和。报告 §1/§3.2 把它算成固定成本，错。
- "wait copy 170→415→259 非单调"是 warm 样本的产物；实测是单调饱和。**报告 §1 的非单调疑点应删**。
- 总量结论不变：专家三项（GU+down+dequant）在 248 tok 上占 **52.1%**，在 1914 tok 上占 **45.7%**。

**处置**：`PROGRESS M5`、方案 §6.5 的相位数字全部换成 rep0 值；W853 顶部加更正条。

### P0-2 `wait copy` 的机理读错了：等的是专家 blob 的拷贝事件，不是"主机拷贝没走 pinned"

`prefill.cpp:3454-3458` 原文是 **D-5 的解释性注释**：*"the stream is issued by its own host thread,
so the thread launching the layers' kernels never waits behind a host copy of an unpinned blob
(**that wait left the GPU idle**: the 'wait copy' / 'dequant' time of the i-quant prompts)"* ——
句子是过去时，讲的是**加 issuer 线程之前**的状态。

而 `kPfWaitCopy` 的实际埋点（`prefill.cpp:4302 / 5193 / 5438 / 5467 / 6599`）后面紧跟的是
`wait_issued(k-1)` / `wait_copied(...)` / `cudaStreamWaitEvent(m.cs, m.copied[slot])` ——
**GPU 在等"专家 blob 的拷贝完成事件"**，拷贝由独立 issuer 线程按 `--pcie-frac` 的节奏发出。
埋点头注释也写明："a gap where the GPU waits (for the host's expert grouping, **or for an expert's copy**)
lands on the phase that was waiting"。

另外 `prefill.cpp` 已在用 `core::PinnedRing up_ring`（`:854`、`:1134`，注释 `#1996: this device's pageable
uploads ... go up from pinned slots`），即"pageable 上传走 pinned 槽"这件事**已经做了**。
`docs` 里还有 `mpt.cpp:514` 记着同一族改造曾把 wait copy 从 3,081 ms 压到 75 ms。

⇒ R15 的判据"改 pinned"方向不明：**该查的是专家 blob 的预取深度/发射节奏（`--pcie-frac`、ring 深度、
`stream_all_min`）**，而不是 pinned。R15 必须重写，否则会白花一次停服。

### P0-3 `gemm_iq_f16_grouped` 在 gfx906 上恒不可达，且它处理的是 IQ 格式

`prefill.cpp:1330-1346`：

```cpp
bool pf_wmma() {
#if defined(__HIPCC__)
    return false;          // ← 我们的构建走的就是这条
#else
    ... 只有 STRATA_PF_WMMA=1 且所有卡 compute capability ≥ 7.0 才 true
#endif
}
```

它的调用点（`:1364`）只在 `pf_wmma()` 为真时把层加进 `wmma_only`。我们的构建是 `hipcc`，
`__HIPCC__` 必定义 ⇒ **这条融合路径在本机不可能被选中**，与"阈值/ring 深度/命中率"无关。

再者，该融合路径吃的是 **IQ 格式**（IQ1_M/IQ4_NL，`iq_row_bytes()>0`）；生产是 **native pack + UD-Q4_K_XL**，
走的是 `prefill.cpp:5376-5382` 的 `iq_dequant_gu_f16()` / `iq_dequant_f16()`（llama.cpp 公式），
**不是** `kernels.cu:3117 blob_dequant`（那条只在 `lay.native==false` 的 Strata Q2_0 pack 上走）。
启动日志 `native pack: /data/packs/ud-q4_k_xl experts` 已确认这一点。

⇒ R14 的问法（"为什么不用融合路径"）在源码里已有答案：**用不了**。真问题变成
"FP16 专家路径的 dequant 能不能省"——答案在 P0-4。

### P0-4 ~~账本与二进制不一致：MMQ 从未编进生产线~~ **【已撤回，2026-11-01 00:4x】**

> **撤回理由（三条，都是硬证据）**：
> ① `build.ninja` 里 `strata_prefill` 的编译行含 **`-DSTRATA_PREFILL_MMQ=1`**（定义来自
>    `CMakeLists.txt:2317`，在 `if(STRATA_ENABLE_CUDA)` 分支内；`STRATA_HIP_GFX906=ON` 会在 `:91-93` 强制
>    `STRATA_ENABLE_CUDA=ON`）⇒ **MMQ 代码在我们的二进制里，且 `mmq::built()` 不是桩**。
> ② `STRATA_PREFILL_MMQ` 这个 **CMake 选项**（`:94`，默认 OFF）只控制 `:145` 的合法性检查和 `:2392` 的
>    `elseif` 备用分支；选项 OFF ≠ 定义缺席。12 个 build cache 的 `OFF` 因此什么也证明不了。
> ③ 我引的"近三次启动 0 条 MMQ 派发行"无效：`MMQ tile` 这条打印来自 W795 的 `patch_mmq_tile_j.py` 补丁镜像，
>    **当前源码里没有这条打印**（`grep -rn 'MMQ tile' src/prefill` = 0）。
>
> **仍然成立的部分**：P112 的 `REJECTED(value=0)` 语义确实是"保留 MMQ"，而 MMQ 现在**确实开着**——账本与二进制
> 一致，不是不一致。**由此产生的新问题见 R17**：`dequant` 相位在 MMQ 路径下到底量的是什么（W795 自己写过
> "dequant（实为 group gather）"），以及有没有层因 `mmq::fits()` 失败落回 FP16。

#### ~~原判（保留原文，作为误判记录）~~

| 检查 | 结果 |
|---|---|
| `CMakeLists.txt:145` | `if(STRATA_PREFILL_MMQ AND NOT STRATA_ENABLE_HIP) FATAL_ERROR` |
| `CMakeLists.txt:88-89` | `STRATA_HIP_GFX906` 与 `STRATA_ENABLE_HIP` **互斥**（FATAL_ERROR） |
| 12 个历史构建 cache（0.2.2 起） | **全部** `STRATA_PREFILL_MMQ:BOOL=OFF`（含 `gfx029-build`、`build-028r`） |
| `prefill.cpp:77-80` | `#ifndef STRATA_PREFILL_MMQ` ⇒ `bool built() { return false; }` |
| 近三次启动（log 79394/79449/79562） | **0 条** `prompt MMQ ...` / `MMQ tile ...` |
| 日志里所有 `MMQ tile` 行 | 在 log 32722–33073，即 2026-10-25 的 W795 实验窗口 |
| `P112` | `REJECTED`，`value=0`，正文"臂 B(+61.1%) 否决" ⇒ 语义是"**保留 MMQ**" |

⇒ 生产今天的 prefill 专家乘积**全部走 FP16 反量化路径**；`STRATA_PREFILL_MMQ` 这个开关在当前构建里是
**惰性变量**（`mmq::built()` 恒 false，`mmq_plan().fallback` 恒 true）。

**但不要据此说"MMQ 值 61%"**：W795 的 +61% 是 **0.2.4p4 镜像 / 0.1.4x 引擎**上量的，
而当前 FP16 路径已经比那时快得多（21.8K 档：那时 54.2 s，现在按 19.4K=27.8 s 折算约 31 s）。
⇒ 正确表述是：**"MMQ 在 0.1.55 上的价值未知，且当前构建拿不到它"**，
判据是打开构建门后的一次 A/B（新增 **R16**）。

**这条同时解释了 W853**：`dequant 20% + GU 19–22% + down 13–14%` 是 FP16 路径的固定形状；
它也是 W851 §2.3「`STRATA_ENABLE_HIP` 与 `STRATA_HIP_GFX906` 互斥把 hipBLASLt 剪掉」的**同一个根因**。
一堵墙挡着两件事（hipBLASLt、MMQ），账本里却只记了前者。

---

## 2 P1（结论或数字错，但不改变大方向）

| # | 问题 | 证据 | 处置 |
|---|---|---|---|
| P1-5 | **三个 A/B 都把 warm 请求当测量行并列**：W850 表 5 行=2 warm+3 实测；W851 表 8 行=2 warm+6 实测；W852 表 8 行=2 warm+6 实测。warm0 的偏差是 +32%（W844 6.00 vs 4.55 s） | `w850_rocm_210857.txt`、`w851_abtbl2_221829.txt`、`w852_ab101_225425.txt` 逐行对照 | 报告表标注 `warm/实测` 分栏；**结论只用实测行**。W844 是唯一做对的（表里只有 6 条实测） |
| P1-6 | 因此 **W851 的"−0.7%"不成立**：去掉 warm 后 <1024 组是 **−0.35%（n=5）**，对照组（1181 tok）是 −0.4% ⇒ **两组完全重合**，"实验组略优"这句话消失 | 上表逐帧重算：333/630/342/557/972 五档 | 判否结论**更强**（不是更弱），措辞改为"与对照不可分" |
| P1-7 | **W852 的回滚件标错**：文档说 `strata166-407.pre-w852` 是 0.2.9t2(7.14)，实测是 **`0.2.9r1`（ROCm 10.1）** | `docker ps -a` + `docker inspect`；`w852_finalize` 日志"旧容器改名 pre-w852"时旧容器已是末臂 B2(10.1) | 真回滚 = 用镜像 `0.2.9t2` 重建 + `STRATA_ROCBLAS_TUNING` 指回 `5.5.0.txt`。文档按此改写 |
| P1-8 | **arm 容器名系统性错位**：`w852-A/t2 ✓`、`w852-B/**t2**`、`w852-A2/**r1**`、`w852-B2/**t2**`；`arm-A2/**r1**`。名字与实际镜像对不上（与 W850 §5 自述的 off-by-one 同族，但 W852 没记） | `docker ps -a` 现取 | 取证只认**启动日志里的 `img=`/`TABLE` 行**；容器名改为 `<臂>-<镜像>-<表>`。这条写进纪律 |
| P1-9 | **W851 §4.1 把社区数当"同引擎"**：xxDoman `llms.txt` 的 +19.7%/+24.2% 是 **2 卡分片（MI50+Radeon VII）/ IQ3_XXS / engine 0.1.43.1 / ROCm 7.2.1 / ctx 131072** 的 regime，文件自己写 "Numbers here are measured on one box and carry their regime" | 原文已核（§5-#5） | 只能作"同代卡存在收益"的旁证，**不能当我们的预期**；§4.1 加 regime 标注 |
| P1-10 | **方案本体没吸收 ROCm 10.1**：`W832_OPT_PLAN_V2.md` 里 grep 不到 `10.1` / `X15`，而生产已切 10.1 + 84 行表。唯一权威件缺了本会话最大的一次环境变更 | `grep -c '10\.1'` = 0 | 新增 **§6.12 userland 面**（ROCm/rocBLAS/表绑定、回滚、禁忌） |
| P1-11 | **登记表停更**：W844–W853 新增 **0 条 P 行**（止于 P229）。ROCm 版本、84 行表、M5 相位口径、MMQ 构建门全部只有 PROGRESS 没有 P 号 ⇒ 违反 §6.9 铁律"同轮入账" | `PARAM_REGISTER.tsv` 尾行 P229 | 补 **P230–P233**（§6） |
| P1-12 | **方案 §6.5 又出现两套排序**：顶部"W853 重排 1/2/3（dequant/wait copy/专家 GEMM）"与下面 13 行编号表（3=R6、4=M5…）并存且冲突 —— 与 AUDIT15 S1 修掉的是同一个病 | `sed -n '461,494p'` | 顶部块改为"**结论摘要，不是队列**"，编号表重排并吸收 R14/R15/R16 |
| P1-13 | **W853 §2 的"短 prompt 每 token 贵 2.7 倍"算不出来**：实测 1084/248=4.37 ms/tok、3328/1914=1.74 ⇒ **2.51×**；用报告自己的数 4.26/1.663=2.56× | 两套数都算过 | 改 **2.5×** |

---

## 3 P2（文档精度 / 口径）

| # | 问题 | 处置 |
|---|---|---|
| P2-14 | W844 §7 写 decode "92/131 vs 86/127"：B 的 p2 是 92/131 ✓，A 的 p2 实际 **83/122**（A2 是 95/133） | 改 83/122 |
| P2-15 | W847 组件"234 文件"vs `find -type f` = **235**：`--verify` 报 234 是**不含 manifest** | 两处都写清口径 |
| P2-16 | `/src` 文件数三个值并存：W847 **8143**（建时）、W848 **8187**、现测 **8185** | 注明"建时快照 vs 运行后 `__pycache__` 重生成"（现测多出的 42 个就是 pyc） |
| P2-17 | W848 的 `hipblaslt/library` 判据已被 W851 §6 自我更正，但 **`SESSION_STATE §3.1` 仍在用它**；同段还写表"60 行"（日志是 `56 rows`，60 是文件行数含 4 行表头） | 改 `SESSION_STATE §3.1` 为 `TensileLibrary_lazy_gfx906.dat` 不存在 + `AlgoGetHeuristic=0`；表改"56 行数据 / 60 行文件" |
| P2-18 | W853 §1 "wait copy 7–14%" 的上限实际 **15.5%**（1239 tok 那行） | 改 7–15.5% 或按 rep0 写 8.9–12.7% |
| P2-19 | W852 §1.1 把 `THEROCK_ENABLE_HIPBLASLTPROVIDER=OFF` 说成"关掉 hipBLASLt"：原文是"**hipDNN provider on top of hipBLASLt**" | 改"关掉 hipDNN 的 hipBLASLt provider" |
| P2-20 | W852 §1.3 引 `ROCm/hipBLASLt#1243` 与 `pytorch#138067`：两者正文**都不含 gfx906**（是 ROCm 6.2 nightly 的另一因，均已 closed） | 降级为"库在不支持架构上会硬报错"的旁证 |
| P2-21 | W850 §5 自述 arm 命名 off-by-one，但没记 **A2 段日志里出现 5.7 的 mismatch 行**（`/data` 日志被所有臂共享、无 mark 的污染）。本轮靠"`rocm: 7.14` + `56 rows` 两行 + 数值同形"才没被带偏 | 记入方法坑；`SESSION_STATE §4` 已有 mark 纪律，补一条"共享日志" |
| P2-22 | 方案 §6.11 内**两条互斥记载并存**：一条"rebase 做不了 ⇒ worktree 重放"，另一条"W845 更正：浅克隆伪影"。前者没标作废；同表"约 40 min 全量编译"也已作废（实测 6.7 s 叠层 + 164/164） | 前者加 **SUPERSEDED（W845）**，后者改实测值 |

| P2-26 | **W847 §6「还剩什么不是 0.2.9」整节已过期**：写着 terminal/seed 是"0.2.4 时代产物"（实际当时不存在，W848 才装）、`/opt/rocm` "仍是 7.14 且这就是最新"（W852 已切 10.1）。同族于 P2-17（同一轮把"不存在"写成"旧版本"） | 该节顶部加作废条；现状只认 `SESSION_STATE §1` 与方案 `§6.12` |

---

## 4 P3（卫生）

- **P3-23** `probe_hblt.cpp:49` 的 `printf("%.4f", res[i].algo)` 把 struct 当 double（8 个 warning）。algos=0 时不触发，但一旦有解就是 UB。
- **P3-24** W849 写"118.9 GiB RAM available"，实测启动行是 **118.7**（同一行每次启动略有浮动）。
- **P3-25** W851 §2.1 的探针输出**当时没落盘**（只留了 `.cpp`），与"可复核"纪律不符。本轮已重跑并落盘：
  `166:~/strata166/data/w856_probe_hblt_101.txt` —— 输出与 W851 引用**逐字一致**
  （`Could not load "TensileLibrary_lazy_gfx906.dat"` / `status=3 algos=0` / 小形状同样 0）。

---

## 5 上网核实的 12 条（不是猜）

| # | 断言（出处） | 核实结果 |
|---|---|---|
| 1 | ROCm 10.1 于 10 月发布，重点是 hipFILE 异步快路 / NUMA 主机内存 / ROCm CLI / LLVM 24（W850 §3、W852 §5） | **对**。chiprook、StorageReview、ROCm consolidated changelog 三源一致；`hipFileReadAsync/WriteAsync` 直走 HIP stream、`hipMemLocationTypeHostNuma` |
| 2 | 10.1 用 amd-smi 取代 rocm-smi（W850 §4） | **对**（changelog 与报道均写 "ROCm SMI removed, migrate to amd-smi"）。我们两代镜像里三个工具都在（实测），遥测走 sysfs、不依赖 smi ⇒ 无影响 |
| 3 | 官方 10.1 兼容矩阵**不含 gfx906**（W848/W850/W852） | **对**。官方 system-requirements 表：MI50 / Radeon PRO VII / Radeon VII 的 gfx906 全为 ❌ |
| 4 | `tensilelite_supported_architectures.cmake` 的 `SUPPORTED_ARCHITECTURES` 无 gfx906，且 `tensilelite_validate_gpu_targets` 会 FATAL（W851 §2.2） | **对**。develop 原文逐字核过；`BASE_ARCHITECTURES` 也无 gfx906；gfx10XX 的注释也与引用一致 |
| 5 | Wizard815/TheRock-gfx906 `GFX906.md`：`there is no vega20 logic`、`no lib/hipblaslt/library/gfx906`、`-DTHEROCK_ENABLE_HIPBLASLTPROVIDER=OFF`（W852 §1.1） | **对**，逐字命中。唯一偏差：该 flag 在原文里写作"hipDNN provider on top of hipBLASLt"（见 P2-19） |
| 6 | mixa3607/ML-gfx906 ★364、有 `rocm-tensile/`、无 hipBLASLt 构建（W852 §1.1） | **对**（★364 实测；描述含 llama.cpp/ComfyUI/Strata/Maya） |
| 7 | Debian `debian-ai` 2024-03：gfx803 编 hipBLASLt 撞 `.amdhsa_accum_offset requires gfx90a+`，结论 "not a library that we're going to be able to port"（W852 §1.2） | **对**，原文逐字（含 `S_8_32_gfx803.s:257`、ROCm 5.7.1、只支持 gfx90a） |
| 8 | `ROCm/hipBLASLt#1243` / `pytorch#138067` 标题是 "Attempting to use hipBLASLt on a unsupported architecture!"（W851 §1.3/W852 §1.3） | **标题对**，但**都已 closed（2024-10）且正文不含 gfx906** ⇒ 只能当旁证（P2-20） |
| 9 | xxDoman/strata-gfx906 `llms.txt`：4K 460.7 vs 384.9（+19.7%）、16K 544.9 vs 438.6（+24.2%）（W851 §4.1） | **数字对**，但 regime 是 2 卡分片 / IQ3_XXS / engine **0.1.43.1** / ROCm 7.2.1（P1-9） |
| 10 | 同一 `llms.txt` 说表默认关、要 `STRATA_HIP_PROMPT_F16=1`，且上游 PR #981 因 `STRATA_ENABLE_HIP` vs `STRATA_HIP_GFX906` 的 gate 编译不出来（W851 §2.3 的旁证） | **对**，与我们的 W793 补丁同因 |
| 11 | rocBLAS 有 vega20 的 Tensile logic（`Logic/archive/vega20_*`），但那是 Tensile 不是 TensileLite（W852 §3-第 3 步） | **对**（rocBLAS 源码目录结构 + AMD 的 TensileLite tuning 文档） |
| 12 | TensileLite 的 tuning 只能返回"其搜索空间内"的核（W852 判"第 3/5 步是墙"的依据） | **对**（AMD 博客原文：search space 决定可返回集合） |

**不需要改方案的**：第 1–6、10–12 条。**要改措辞/降级的**：第 8 条（P2-20）、第 9 条（P1-9）。

---

## 6 台账与文档同步（本轮已改）

| 文件 | 改动 |
|---|---|
| `deploy/W850_ROCM_AB.md` / `W851_TABLE_AND_ROCM.md` / `W852_ROCM101_CUTOVER.md` / `W853_PHASE_PROFILE.md` | 顶部加**更正条**，指向本件对应 P 号（保留原文，不篡改历史） |
| `deploy/W832_OPT_PLAN_V2.md` | §6.5 顶部块改"结论摘要"并重排；加 **R16（MMQ 构建门）**；新增 **§6.12 userland 面**；§6.11 两条互斥记载标 SUPERSEDED |
| `deploy/PROGRESS.tsv` | `M5` 备注换 rep0 数；`R14/R15` 判据重写；`X15` 回滚件更正；**新增 `R16`**；`X12` 的"镜像仍 0.2.8p2"标作废 |
| `deploy/params/PARAM_REGISTER.tsv` | 新增 **P230**（ROCm 10.1 + 84 行表）、**P231**（相位口径：warm vs rep0）、**P232**（MMQ 账本-二进制不一致 / 构建门）、**P233**（`wait copy` 埋点语义） |
| `deploy/SESSION_STATE.md` | §1 镜像/表/env 更新到 0.2.9-101；§3.1 hipBLASLt 判据换成 W851 §6 的版本；§4 补"共享日志"坑；§5 文档地图加 AUDIT16 |
| `deploy/AUDIT_INDEX.md` | 加 AUDIT16 行（覆盖 W844–W853，P0 4/P1 9/P2 9/P3 3）+ 未结清表更新 |
| `deploy/AUDIT_LEDGER.tsv` | 不动（该文件是 AUDIT12 的机械产物，AUDIT13/14/15 亦未追加，保持一致） |

**新增的队列项 R16**（写进 `PROGRESS.tsv` + 方案 §6.5）：

> **在 `STRATA_HIP_GFX906` 下打开 `STRATA_PREFILL_MMQ`**（`CMakeLists.txt:145` 那一条 `NOT STRATA_ENABLE_HIP`
> 放宽成 `NOT (STRATA_ENABLE_HIP OR STRATA_HIP_GFX906)`，与 W793 给 rocBLAS 门做的事同型），
> 重建 → 单臂 A/B（`STRATA_PREFILL_MMQ=1/0`，read 六档 + 相位表）。
> **判据**：read ≥5% 才采纳（引擎级）；<5% 则记 DONE_NEG 并把"MMQ 不可用"写进 P112 备注。
> **成本**：一次构建（增量约 2–3 min，MMQ 模板实例已在 `libstrata_mmq.a` 里）+ 一次停服 A/B。
> **风险**：MMQ 走 dp4a/int8 路径，提示侧舍入与 FP16 不同 ⇒ 若采纳，必须同时过提示侧 KL 门（`.0139` 标尺）。

---

## 7 生产实况（本轮现取，未动）

| 项 | 值 |
|---|---|
| 容器 | `strata166-407` = `538c722f0057`，`strata-gfx906:0.2.9-101`，started `2026-10-31T15:42:42Z`，**restarts=0** |
| 镜像 | `sha256:d4afd5f5…`，15,074,717,290 B（15.07 GB）；`0.2.9r1` 与它同 ID |
| ROCm / rocBLAS / HIP | **10.1.0 / 5.7（`librocblas.so.5.7`）/ 7.16.26323** |
| 表 | `/data/gfx906-rocblas-5.7.0.txt`，88 行（84 数据 + 4 头）；启动行 `rocBLAS tuning enabled (84 rows, 75 with a solution … 5.7.0.962d0059)` |
| args / env | 33 / **6**（`STRATA_ROCBLAS_TUNING=/data/gfx906-rocblas-5.7.0.txt`，无 `STRATA_PREFILL_TIMING`） |
| `/src` | **8185** 文件；`verify_tip.sh` 5319 个 git 文件逐位相同、缺失 0 ⇒ **TIP-OK @ `aef9d256`** |
| 引擎 | `/data/bin/strata-0.1.55g`，md5 `29b15bb4…` = `gfx029-build/strata` |
| 门禁 | **GATE PASS（17 项）**，`img=strata-gfx906:0.2.9-101` |
| 运行时 | `slots=7463`、`vram_free=920`、`pcie=0.20`、`cc.evictions=0`、`pcie_rx 0.01 MB` |
| PLE | 最近三次启动均 `--ple-io ram chosen by the residency policy`（W849 的 X1 结论**当前成立**）；`mlock failed` 每轮都在 |

> 注：`grep -m2 ple-io` 会抓到 10 月 20 日的 `--ple-io mmap` 旧行 —— 查这类"当前策略"必须 `tail`，不能 `-m2`。
> 本轮自己踩了一次，记进 `SESSION_STATE §4`。

---

## 8 自检

| 检查 | 结果 |
|---|---|
| 范围机械性 | `audit12_scope.py`：W844–W853 提及数 0，W843 及以前 >0 |
| 数据可复现 | 每条 A/B 数字都能在 `data/w85*.txt`/`*.json` 找到原行；W853 的 rep0 三行已列全文 |
| 机理可复核 | P0-2/3/4 都给了 `file:line` 与调用者；MMQ 结论有 5 条独立证据（CMake 门、12 个 cache、桩、日志、二进制字符串） |
| 上网 | 12/12 查过；2 条降级（P2-20、P1-9） |
| 台账 | `ledger_audit.py` exit 0（欠账 0）；`progress.py` 见 §9 |
| 生产 | 未动：本轮只读 + 一个 throwaway 容器跑探针（`--rm`，不挂 `/data` 写） |
| 一个自己承认的失误 | P3-25：W851 的探针输出当时没落盘；本轮补跑才让它"可复核" |

## 9 进度（改动后，实跑）

```
块 10 ／ 条 100 ／ 已结 43（43.0%）      ← 本轮 +R16（分母 99→100）、M4 结案（+1）
主线（不含 28 个死块）= 72 条：已结 43（59.7%）
台账对账：登记表未结 15 / PROGRESS 认领 15 / 欠账 0（exit 0）
```

`round_report.py --write` 已生成 `deploy/STATUS_2026-11-01.md`（三节口径）。
`PROD_BASELINE.tsv` 已推进到当前：started `15:42:42Z`（W853 的 m5 restore 让它变了）、`src_files 8185`、
组件"`--verify` 234 / `find` 235"两种口径并列。

---

## 10 整改台账（26/26 全部有落点）

> 口径：**每条都要有"落在哪个文件的哪一句"和"怎么复核"**，不接受"已知悉"。
> 状态只有两种：**FIXED（已改文件）** / **FIXED+DOC（已改 + 写进纪律）**。
> 复核统一三条命令：`python tools/audit_recheck.py`（本表逐条跑，**26/26 PASS**）、
> `python tools/plan_lint.py`（待办是否都在方案里）、`python tools/ledger_audit.py`（欠账）。
> **本表不是声明，是可执行的**：最后一列写的是真命令，跑不过就是没整改。

| # | 处置 | 落点 | 复核 |
|---|---|---|---|
| P0-1 | 相位表按 rep0 重列；M5/R14/R15 与方案 §6.5 顶部换成 rep0 数；W853 顶部写"原表作废" | `AUDIT16 §1-P0-1`、`PROGRESS M5`、`W853` 顶部、`W832 §6.5` | `grep -n "248/1162/1914" deploy/PROGRESS.tsv` |
| P0-2 | R15 判据重写为"预取深度/发射节奏"；`P233` 登记语义更正；`SESSION_STATE §4` 加一条坑 | `PROGRESS R15`、`PARAM_REGISTER P233`、`SESSION_STATE §4`、`W832 §6.2 R15` | `grep -c "wait_copied" deploy/W832_OPT_PLAN_V2.md` |
| P0-3 | R14 判据重写为"摊薄空间"；写明 `pf_wmma()` 在 `__HIPCC__` 恒 false | `PROGRESS R14`、`W832 §6.2 R14`、`W853` 顶部 ④ | `ssh albus@192.168.50.166 "sed -n '1330,1334p' ~/strata166/gfx029/src/prefill/prefill.cpp"` |
| P0-4 | **撤回**：R16 撤下队列、P232 改为"选项≠定义"的更正、新增 R17（MMQ 层分布诊断）；证据链与误判原因见 §1-P0-4 顶部与 §11 | `PROGRESS R16=DONE_NEG`、`P232`、`W832 §6.2 R16` | `ssh albus@192.168.50.166 "grep -m1 -c STRATA_PREFILL_MMQ=1 ~/strata166/gfx029-build/build.ninja"` |
| P1-5 | 三份 A/B 顶部加"warm/实测必须分栏"更正条；`P231` 立为纪律 | `W850/W851/W852` 顶部、`PARAM_REGISTER P231` | `grep -c "warm" deploy/W851_TABLE_AND_ROCM.md` |
| P1-6 | W851 更正条写明"去 warm 后 −0.35% ⇒ 与对照重合，判否更强" | `W851_TABLE_AND_ROCM` 顶部 ① | `grep -c "−0.35%" deploy/W851_TABLE_AND_ROCM.md` |
| P1-7 | W852 回滚件改成"用 0.2.9t2 重建 + 表指回 5.5"；`PROGRESS X15` 同步；方案 §6.12 再写一次 | `W852` 顶部 ②、`PROGRESS X15`、`W832 §6.12` | `grep -c "0.2.9r1" deploy/W852_ROCM101_CUTOVER.md` |
| P1-8 | 纪律：取证只认日志 `img=`/`TABLE` 行，容器名要带镜像 | `W852` 顶部 ③、`SESSION_STATE §4`（共享日志条） | `grep -n "img=" deploy/W852_ROCM101_CUTOVER.md` |
| P1-9 | W851 §4.1 加 regime 标注；AUDIT16 §5-#9 记录 | `W851_HIPBLASLT_VERDICT §4.1` | `grep -n "IQ3_XXS" deploy/W851_HIPBLASLT_VERDICT.md` |
| P1-10 | 方案新增 **§6.12 userland 面**（ROCm 10.1 / 表绑定 / 回滚 / 禁忌） | `W832 §6.12` | `grep -c "10.1.0" deploy/W832_OPT_PLAN_V2.md` |
| P1-11 | 登记表补 **P230–P233** | `PARAM_REGISTER` 尾部 | `tail -4 deploy/params/PARAM_REGISTER.tsv` |
| P1-12 | §6.2 改"条目台账"、§6.5 改"只排序"；两处分工写死 | `W832 §6.2 标题`、`§6.5 排序规则` | `sed -n '/### 6.2 /,/### 6.3 /p' deploy/W832_OPT_PLAN_V2.md` |
| P1-13 | "2.7 倍"改 **2.5×** | `W853` 顶部 ⑥、§2 注 | `grep -n "2.5×" deploy/W853_PHASE_PROFILE.md` |
| P2-14 | decode 接受率改 83/122 | `W844 §7` | `grep -n "83/122" deploy/W844_REBASE_029.md` |
| P2-15 | 组件 234/235 两种口径写清 | `W847 §0`、`W832`（组件行） | `grep -n "234/235" deploy/W847_FULL_029_IMAGE.md` |
| P2-16 | `/src` 8143 标"建时快照"，运行后 8185 | `W847 §3` | `grep -c "8185" deploy/W847_FULL_029_IMAGE.md` |
| P2-17 | W848 的旧判据划掉；`SESSION_STATE §3.1` 换成探针判据 | `W848 §2`、`SESSION_STATE §3.1` | `grep -c "hipblaslt/library" deploy/SESSION_STATE.md`（应为 1，且带"作废"） |
| P2-18 | wait copy 上限改 12.7%（rep0）/15.5%（warm） | `W853` 顶部 ⑥ | `grep -c "15.5%" deploy/W853_PHASE_PROFILE.md` |
| P2-19 | `HIPBLASLTPROVIDER` 措辞改"hipDNN 的 provider" | `W852_HIPBLASLT_SELFBUILD` 顶部 ① | `grep -n "hipDNN" deploy/W852_HIPBLASLT_SELFBUILD.md` |
| P2-20 | 两个 issue 降级为旁证 | `W851_HIPBLASLT_VERDICT` 顶部 ② | `grep -c "旁证" deploy/W851_HIPBLASLT_VERDICT.md` |
| P2-21 | W850 §5 补"A2 段被 B 臂日志污染"；`SESSION_STATE §4` 加共享日志坑 | `W850 §5`、`SESSION_STATE §4` | `grep -n "共写同一个" deploy/SESSION_STATE.md` |
| P2-22 | §6.11 的"rebase 做不了"标 **SUPERSEDED（W845）**；"40 min"改实测 | `W832 §6.11` | `grep -n "SUPERSEDED（W845" deploy/W832_OPT_PLAN_V2.md` |
| P2-26 | W847 §6 顶部加作废条（两行错误） | `W847 §6` | `grep -c "AUDIT16 P2-26" deploy/W847_FULL_029_IMAGE.md` |
| P3-23 | 探针 printf 格式 bug 记录在案（不影响 algos=0 的结论） | 本件 §4 | `grep -c "res\[i\].algo" albus/w851/probe_hblt.cpp` |
| P3-24 | 118.7 vs 118.9 记录在案 | `W849 §3` + 本件 §4 | `grep -c "118.7" deploy/W849_TIP_AND_QUEUE.md` |
| P3-25 | 探针重跑并落盘 | `166:data/w856_probe_hblt_101.txt` | `ssh albus@192.168.50.166 "grep -c algos=0 /home/albus/strata166/data/w856_probe_hblt_101.txt"` |

### 10.1 整改后新立的两个 gate

| gate | 作用 | 归属 |
|---|---|---|
| `tools/plan_lint.py` | **A** PROGRESS 未结项 / **B** 登记表未结项 / **C** 正文带 id 的待办 / **D** 方案里的 R 号反向 —— 四向对齐，exit 0 才算收工 | 收工前与 `ledger_audit.py` 一起跑 |
| `deploy/ID_MAP.tsv` | 账本 id（M1/U2/G3…）↔ 方案 id（R6/R3/R9…）的唯一对照 | 任何一边改名，先改这张表 |

---

## 11 误判复盘：P0-4 为什么会错（写下来，防止再犯）

| 我做了什么 | 为什么看起来对 | 实际错在哪 |
|---|---|---|
| 查 `CMakeCache.txt`，看到 `STRATA_PREFILL_MMQ:BOOL=OFF`，12 个构建目录全 OFF | 一个开关全 OFF，很像是"没编" | **CMake 选项 ≠ 编译定义**。选项只管 `:145` 的合法性检查与 `:2392` 的备用分支；真正决定代码进不进二进制的，是 `:2317` 在 `STRATA_ENABLE_CUDA` 分支里**无条件**给的 `-DSTRATA_PREFILL_MMQ=1` |
| 看到 `prefill.cpp:77` 的 `#ifndef STRATA_PREFILL_MMQ → built(){return false;}` | 桩确实存在 | 桩只在**定义缺席**时编译；我们的定义在场，桩被 `#ifndef` 排掉 |
| 数日志里的 `MMQ tile` / `prompt MMQ` 行，近三次启动为 0 | "没有派发就不打印" | 这两条打印分别来自 W795 的补丁镜像与 `DIRECT/GROUP_SORT` 环境变量，**默认路径本来就不打印**；"缺失"不是证据 |
| 于是推出"生产走 FP16 专家路径" | 三条弱证据同向 | 没做**最直接**的一步：看 `build.ninja` 里那个目标到底带了哪些 `-D` |

**新纪律（写进 §6.9 的下一条）**：
> **判"某功能在不在二进制里"只认三样**：① 该目标在 `build.ninja`/`compile_commands.json` 的 `-D` 列表；
> ② `nm`/`strings` 里该功能的**独有**符号或字符串；③ 运行期**无条件**打印的横幅。
> **不认**：CMake 选项、cache 变量、条件打印的缺失、以及"别人的镜像里出现过"的日志。

这条与 AUDIT14 的"采证带 mark"是一对：那条防"抓到旧行"，这条防"没抓到就当没有"。
