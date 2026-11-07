# W788 R5 归因：HC 投影的 16.1% 是 occupancy 问题，不是寄存器、不是带宽

> 队列位置：`W787 §4` 的 R5（HC 归因，16.1%，多轮场景下 decode 最大单项）。
> 方法：**不注射、不改码**，先用源码 + pack 索引 + 已有阶段计时算出理论下限，找差在哪里。

---

## 1 HC 是什么（从 pack 索引读到的结构，不是猜）

`/data/packs/huihui-ud-iq4_xs/index.txt`：

| tensor | 形状 | 每层字节 |
|---|---|---|
| `hc_attn_down.weight` | **10240 -> 320** | 6,553,600（bf16，2 B/元素） |
| `hc_attn_up.weight` | **320 -> 10240** | 6,553,600 |
| `hc_ffn_down.weight` | 10240 -> 320 | 6,553,600 |
| `hc_ffn_up.weight` | 320 -> 10240 | 6,553,600 |
| `hc_attn_inject.weight` | 10240 × 4 | 81,920 |

- **48 层**（`blk.0` .. `blk.47`），每层 4 个 HC 矩阵 + 1 个 inject
- `HC = 4`（streams，源码 `fused_gr.cu:30`）、`LR = 320`（`hc_lr`，`:32`）、hidden `N = 2560`
- down 的输入是 4 个 stream 拼起来的 `HC × N = 10240`

=> HC 的语义：**把 4 路残差的 10240 维压到 320（down），过一下非线性，再升回 10240（up）**，每层 2 组（attn / ffn）。

## 2 理论下限 vs 实测（这是本节的硬结论）

Q8 副本（`STRATA_HC_Q8=1`）下每个矩阵 10240 × 320 × 1 B ≈ **3.28 MB**：

```
48 层 × 4 矩阵 × 3.28 MB = 629 MB / 窗口
MI50 HBM ≈ 805 GB/s  =>  0.78 ms / 窗口（纯权重读取的地板）
```

实测（M 档 21,827 token，97 窗口稳态，`STRATA_VERIFY_PROFILE=1`）：

| 子项 | GDN hc0 | GDN hc1 | QSA hc0 | QSA hc1 | 合计 |
|---|---|---|---|---|---|
| norm | 0.49 | 0.06 | 0.02 | 0.02 | 0.59 |
| **down** | 1.33 | 1.27 | 0.44 | 0.44 | **3.48** |
| **up** | 1.28 | 1.28 | 0.42 | 0.42 | **3.40** |
| 小计 | 3.10 | 2.61 | 0.88 | 0.88 | **7.42**（列相加 7.47，与 `P91` 的 HC 组取 7.42，差 0.7% 为舍入） |

=> **实测 7.42 ms vs 地板 0.78 ms = 9.5 倍差。** 所以 HC 不是"带宽结构性地板"，是效率问题。

（顺带一个未解释的异常：`hc0 norm 0.49` 是 `hc1 norm 0.06` 的 **8 倍**，而两者 down/up 几乎完全对称。norm 只值 0.59 ms（1.3%），先记录不追。）

## 3 down 的根因：41 个 block，19 个 CU 在空转

源码 `fused_gr.cu:40-42`：

```cpp
constexpr int THREADS = 256;
constexpr int WARPS   = THREADS / 32;      // 8
constexpr int DOWN_BLOCKS = LR / WARPS;    // 320 / 8 = 40 （+1 个 inject block = 41）
```

`gr_down_multi_kernel`（`:306`）的并行方式：**一个 warp 负责一个输出 row**（row ∈ [0,320)），K=10240 由 warp 内 32 lane 分 10 个 8 元素块。

配合 shared 用量（`:308` `extern __shared__ float tile[]`，`[T][TILEV]`）：

| 量 | 值 | 后果 |
|---|---|---|
| grid | **41 blocks** | GPU 有 **60 CU**（`rocminfo` 实测）=> 19 个 CU **完全空闲**（68% 覆盖） |
| shared | 3.33 × 2560 × 4 B ≈ **34 KB** | 每 CU 64 KB => **1 block/CU** |
| wavefront/CU | 256 线程 = **4 个 wavefront** | 每 CU 容量 **40 wavefront**（`Max Work-item Per CU 2560 / 64`）=> **10% 占用** |
| 合起来 | 68% × 10% ≈ **6.8%** | 1/0.068 = 14.7 倍，与实测 9.5 倍同量级 |

> **[2026-10-25 06:3x `AUDIT7 P1-2` 更正]** 原表按 CUDA 语义算成 `8 warps` / `20%` / `13.6%`，**错 2 倍**。
> gfx906 的 `Wavefront Size: 64`（`rocminfo` 实测），256 线程 = 4 个 wavefront；内核虽按 32 lane 分组
> （`:310` `warp = t >> 5`），但**两个 32-lane 组共用一个 wavefront**，所以只占 4 个 wavefront 槽。
> 数值更正后，9.5 倍与 14.7 倍（纯占用率预期）之间还差一截 => 占用率不是**唯一**损失源。

**根因要分开说，这一点原文混在一起了：**

- **主因是 block 数**：41 < 60 CU，19 个 CU 空转（68% 覆盖）。
- **shared 在这里不是约束**：它只决定"每个 SM 能放几块"，而**我们只有 41 块，比 CU 还少**，每 CU 本来就最多 1 块。
  所以 `:301` 那句 `smaller tiles raise how many blocks share an SM` 描述的是"块数 > CU"的场景，**在我们这里不成立**。
  这个区分直接决定路径 A 该不该做，见 §5。

`W785 §2.2` 已经排除了"寄存器溢出"（实际在跑的 `gr_down_multi_kernel<2560,8,true>` 是 114 VGPR / priv=0），
本轮把第二个可能也排除了：**不是带宽、不是溢出。**

## 4 up 的根因不同：并行度够，但 K 太小

`gr_up_multi_kernel`（`:367`）反而是大 grid：

```cpp
constexpr int UPM_COLS = 16;                    // 每 block 16 列 x 4 streams = 64 rows
constexpr int UPM_BLOCKS = N / UPM_COLS;        // 2560 / 16 = 160
```
shared 只有 `lo[MAX_T][LR]`（10 KB）+ `g[MAX_T][HC][UPM_COLS]`（2 KB）= **12 KB** => 5 blocks/CU，
grid 640 blocks => 占用是满的。

但 **K 只有 320**（up 是 320 -> 10240，归约长度 320），每 block 的计算量 = 64 row × 3.33 token × 320 = 68K MAC，
分摊到 256 线程 = 266 MAC/线程。**这是 latency bound，不是 occupancy bound。**

=> down 与 up 时间几乎相同（3.48 vs 3.40），但**原因完全不同**，不能用同一个改法。

## 5 两条可执行路径

### 路径 A（最小验证，改 1 个模板实参）—— **[已判无效，不要做]**

> **[2026-10-25 06:3x `AUDIT7 P1-3` 源码级判定：此路径结构上不可能有效。R5 已按此路径做了一半，裁定见 `W789_R5_TILEV_VERDICT.md`。]**
>
> 1. **块数不变**：`DOWN_BLOCKS = LR/WARPS` 与 `TILEV` 无关，grid 恒 41；而 CU 有 60。
>    **块数比 CU 少时，减小 shared 不会有第二块落到同一 CU** —— 占用率一点都不会变。
> 2. **小 tile 的唯一收益条件不成立**：它省的是"8 token 装进一次 launch"。实测 `chunk = 64KiB/(tv*4)`：
>    `tv=2560 -> 6`、`tv=1280 -> 8`；而我们的 `avg T = 3.33-3.47`，**两种 tile 下都只有一次 launch**。
> 3. **预取深度减半**：`TQ = TILEV/8/32` 从 10 降到 5，每 lane 在飞的权重块减半，方向是负的。
>
> 原文写的"每 CU 可从 1 block 升到 3 blocks"是本路径的核心假设，而它在 41 < 60 时不成立。

原方案（供留档）：`TILEV` 2560 -> 1280，shared 34 KB -> 17 KB；风险是 `TQ` 从 10 变 5。

### 路径 B（**唯一有效路径**，参考 routeK 的 KCHUNK）—— 治的是 block 数
`dense_gemv_gfx906.cu:10-18` 的结构：**block 覆盖 RPT 个 row，threads 切 K-chunk，KCHUNK ∈ {512,1024,2048,4096}，KSPLIT = K/KCHUNK**。

HC down 用这个思路：N=320 / RPT=4 => 80 blocks x KSPLIT(10240/2048=5) = **400 blocks**，每 block 256 线程。
代价：K-split 要 reduce（320 个输出点 x 5 段）。routeK 用打包 CAS，我们输出是 fp32，需要 atomic 或第二遍归约。
**注意 routeK 的 `K-split GEMV -> REJECTED` 不适用**——它否的是 M=1、N 大（能填满 GPU）的 dense GEMV，那里拆 K 只增加 reduce 开销；我们是 N=320 填不满，拆 K 正是增加并行度。

## 6 工具：`rocprofv3` 在 166 与镜像里都有

```
rocprofiler-compute version: 3.7.0 (release)
/opt/rocm/bin/{rocprofv3, rocprofv3-avail, rocprof-compute, rocprof-sys-run, rocprof-attach}
```

本轮所有结论都是从**源码 + ELF 资源 + 阶段计时**推的，还没上 profiler。下一步若要定论（尤其路径 B 的 reduce 开销、up 的 latency 归因），用 `rocprofv3 --kernel-trace --stats` 跑一个 S 档请求即可（需停生产约 3 分钟）。

## 7 为什么这条比之前的项值钱

| 项 | 占比 | 是否已到地板 |
|---|---|---|
| 专家流 VRAM hits 8.88 | 19.2% | **是**（命中后必须读） |
| **HC down + up 6.88** | **14.8%** | **否**（9.5 倍差，且根因明确是 41 blocks） |
| 量化 + dense GEMV 6.13 | 13.3% | 未知（R3 待扫） |
| router 3.74 | 8.1% | 否（fp64） |
| 注意力 3.31 | 7.2% | 否（但改答案） |

=> **HC 是目前唯一"占比大 + 明确没到地板 + 根因可量化"的项。**

## 8 本轮没做的（明确划界）

- 没有改任何源码、没有重编、**没有动生产**（只读源码与日志）
- 没有上 profiler（记录为下一步）
- `hc0 norm` 0.49 vs `hc1 norm` 0.06 的 8 倍不对称未追（只值 1.3%）
- 路径 B 的 reduce 方案没有设计细节（要等 profiler 确认 down 的实际 stall 原因）

---

## 9 profiler 实测（工具打通，首次采样不完整）

### 9.1 环境

```
/opt/rocm/bin/rocprofv3   rocprofiler-compute 3.7.0 (release)   git 418cd5f63
```
主机与镜像内都有；`--kernel-trace --stats` 可用，输出 `rocpd_*` 系列 SQLite 表（21 张）。

关键表与列（实测）：
- `rocpd_kernel_dispatch`：`kernel_id`、`start`/`end`（纳秒）、`grid_size_x`、`workgroup_size_x`、`private_segment_size`
- `rocpd_info_kernel_symbol`：`id`、`kernel_name`、`display_name`、`arch_vgpr_count`、`sgpr_count`、`group_segment_size`

聚合脚本已落盘：`deploy/tmp` 之外的 `albus/tune/_prof_top.py`（按 busy_ms 排序，带 grid/block/priv/vgpr）。

### 9.2 两次采样的结果

| 次 | span | dispatches | distinct kernels | busy | 覆盖 |
|---|---|---|---|---|---|
| 1 | 52.8 s | 20,351 | 131 | 14,348 ms | **模型加载阶段**（请求被 503 挡了，health 早于模型就绪） |
| 2 | 71.8 s | 3,032 | 66 | **93.7 ms** | decode 阶段，但**明显不完整** |

第 1 次的 top（加载阶段，仅供对照）：
`Cijk_Alik_Bljk_HSS_BH_MT128x64x16` 17.2% / `Cijk_..._MT64x32x8` 16.9% / `mul_mat_q<21,64>` 16.1% /
`strata::kernels::a...` 13.5% / `mul_mat_q<20,64>` 7.6% / `gdn_re` 4.8%（36 次 × 19.0 ms）。

第 2 次（decode）不可用的判据：
- **3,032 dispatches 覆盖不了一个 96 窗口的请求**（按引擎自己的阶段表，每窗口约 100 个 dispatch，应有 ~9,600 条）
- 榜首是 `__amd_rocclr_fillBufferAligned` 226 次 / **77.4 ms / 82.6%** —— 这是 HIP 的 memset，不可能主导 decode
- 引擎自报 decode ≈ 300 token × 22 ms ≈ 6.6 s，而 busy 合计只有 93.7 ms

=> **rocprofv3 在高频 dispatch 下丢了记录**（缓冲上限），需要 `--kernel-trace-buffer-size` 一类参数或缩短采样窗口。

### 9.3 结论：本轮不采用 profiler 数据

第 8 节的两条结论（9.5 倍差、41 blocks / 13.6% occupancy）**全部来自源码 + ELF 资源 + 引擎阶段计时**，不依赖 profiler。
profiler 目前的产出是**基础设施**（表结构、SQL、聚合脚本、以及"要调 buffer"这个坑），不是结论。

## 10 运维失误（必须记）

**生产停了 10 分钟**（05:28-05:38）。

- 直接原因：`_prof_run2.py` 用 Python 的 `try/finally` 保证恢复，但父进程被 SIGTERM 终止，`finally` 没走完，`strata166-407` 停在 stopped。
- 结构性原因：**恢复动作依赖父进程存活**。这与我 2026-09 踩过的"中断导致 trap 未执行，生产停 21 小时"是**同一类错误**。
- 正确做法（已写进纪律）：恢复逻辑必须放在**远端的 detached 守护**里，例如
  `nohup sh -c '...profile...; docker start strata166-407' &` 再配 `trap EXIT`，而不是靠本地脚本的 finally。
- 已恢复并复核：`loaded: true`、真实请求三轮 `4,660 ms -> 642 ms（reused 1,524）-> 556 ms（reused 1,552）`。
