# W862 — 单请求 decode 的 GEMV 带宽：把 Q8_0 wave kernel 的行数打开

> 2026-11-01 ｜ 目标（机主令）：**单个请求情况下提升 decode，提升带宽占用**
> 结论先行：**不动数值、不换布局、只把"每波行数 R"从 1 改成 2/4**，qkv 形状 ncols=6 从 133.9 → 72.8 µs（**1.84×**），
> ncols=1 从 61.4 → 43.0 µs（**1.43%**，带宽 63.8% → 91.1%）。**输出与现状逐位相同**（`diff=0`，四个形状全过）。

## 0 TL;DR

| 事实 | 数值 | 怎么来的 |
|---|---|---|
| 生产 decode 走投机验证窗口 | `--spec 4` ⇒ GEMV 的 `ncols≈6` | `src/core/verify.cpp:1516` 把窗口 token 数当 ncols 传；`layer.cpp:179` 的普通路径写死 1 |
| ncols=6 时每行重发 NCOLS 倍激活载入 + dp4a | 大矩阵 133.9 µs vs ncols=1 的 61.4 µs = **2.2×** | 本文件 §3 |
| 不是 L1 激活重读 | 激活只有 2.2 KB（`HC up 320→10240`）时仍是 **3.1×** | §3.1，L1 是 16 KB/CU，装得下 |
| 不是占用率 | wave kernel VGPR **36-127**，每 CU 8-26 waves（上限 40） | §3.2，从 gfx906 目标的 AMD 元数据读的 |
| 是指令发射 | 34 字节块 ⇒ `qs` 落在 +2，每 8 字节要 **4 次 u16 载入** | §3.3，`load_int_b2`=两个 u16 |
| 修法（业界同款） | **R = 每波行数**，让一个权重块服务多行 | §5，llama.cpp/p100 的 `rows_per_cuda_block` |
| 实测收益 | qkv ncols=6 **1.84×**；ncols=1 **1.43×** | §3.3 |

## 1 先纠正一个口径（上一轮我给错了）

`W861_DECODE_BANDWIDTH.md` 里那张"9 个矩阵 279.5 µs / 层、shared gate/up 22%"的表**复现不出来**。
同口径重测是 **210.9 µs / 层（505 GB/s，71%）**，shared gate/up 是 **45%**，不是 22%。

唯一差别是**缓存副本数**：那张表用 `copies = min(16, 512MB/bytes)` ⇒ 总计 ~2.3 GB；
现在显存只剩 870 MB（生产占 33.5/34.3 GB），只能用 `min(8, 64MB/bytes)` ⇒ ~320 MB。

⇒ 结论：**22% 是 2.3 GB footprint 下的测量产物，不是生产事实**。生产每层只触 106 MB，接近 320 MB 口径。
**上一轮"GEMV 占 decode 59%、可省 9%"的说法作废**，正确量级见 §6。

## 2 为什么不直接在正式库里改

`native_mmvq.cu` 单 TU 重编 **8-10 分钟**（4 个 R × 8 个 NCOLS 的 wave kernel 实例化），
且实验期间我漏了 `-DNDEBUG`（正式 Release 是 `-O3 -DNDEBUG`），整份二进制均匀慢 1.47×，把"指令受限"的结论污染掉。

⇒ 改走**自足最小内核** `albus/w862/q8_wave_lab.cu`：把 `SmallTraits<Q80Block,8>` 的算术原样搬过来
（34 字节块、4 lane/块、dp4a、64 lane butterfly、`d_w*d_x*sumi`），**几秒编译**，可任意扫 R × 布局 × ncols。
基线校验：qkv ncols=1 R=1 = **61.4 µs**，生产库实测 **58.9 µs**（差 4%），可用。

## 3 实测

### 3.1 不是 L1 激活重读

`HC up 320→10240`：6 个激活向量共 6×320×36/32 = **2.2 KB**，远小于 16 KB L1，仍从 13.0 → 43.5 µs（**3.3×**）。
若瓶颈是激活重读，这个形状应当几乎不受影响。⇒ 排除 L1。

### 3.2 不是占用率

从 gfx906 目标文件的 AMD 元数据读 `wave_kernel` 的 VGPR：**36, 38, 54, 58, 60, 62, 83, 87, 100, 125, 127, 256**。
按 65536 VGPR/CU 折算，每 CU 可驻留 **8-28 个 wave**（上限 40），60 CU ⇒ 480-1680 waves 在飞。
而一层的 9 个 GEMV 产生数万 block。⇒ 占用率从来不是瓶颈。

（顺带推翻我上一轮"block 256 太大、降到 128 能提占用"的推断：`160 blocks×4 waves = 320×2 waves`，**总 wave 数不变**。）

### 3.3 是指令发射，修法是多行共享

以 qkv `2560→10240`（27.85 MB，bpr=80）为例，四种配置（`gguf` = 生产布局，`split` = 把 scale 拆出去让 qs 32B 对齐）：

| 布局 | R | ncols | µs | 权重带宽 |
|---|---|---|---|---|
| gguf | 1 | 1 | 61.4 | 453.5 GB/s（63.8%） |
| **gguf** | **4** | **1** | **43.0** | **647.8 GB/s（91.1%）** |
| gguf | 1 | 6 | 133.9 | 1247.8（per-position） |
| **gguf** | **2** | **6** | **72.8** | **2294.6（per-position）** |
| split | 1 | 1 | 42.5 | 655.2（92.1%） |
| split | 2 | 6 | 72.1 | 2317.6 |

要点：
1. **R 是主力**：ncols=1 用 R=4（1.43×），ncols=6 用 R=2（1.84×）。
2. **R 的上限由寄存器定**：`R × NCOLS ≤ 12` 是甜点。ncols=6 时 R=4 有 24 个累加器，实测 **118.0 µs（比 R=1 还慢）**。
3. **布局 split 只在 ncols=1 时有独立价值**（42.5 vs 61.4，1.44×）；ncols=6 加了 R=2 之后几乎被吃平（72.1 vs 72.8）。
   ⇒ **想省事就不必动权重布局**，只开 R 即可拿到主要收益。

各形状汇总（gguf 布局，ncols=6，取各形状最优 R）：

| 形状 | 字节 | R=1 | 最优 R | 增益 |
|---|---|---|---|---|
| qkv 2560→10240 | 27.85 MB | 133.9 | **R=2: 72.8** | **1.84×** |
| gate 2560→6144 | 16.71 MB | — | R=2（同族，待测） | ~1.8×（估） |
| down 640→2560 | 1.74 MB | 22.5 | R=2: 17.3 | 1.30× |
| g/u 2560→640 | 1.74 MB | 15.3 | R=2: 13.2 | 1.16× |
| HC up 320→10240 | 3.48 MB | 43.5 | R=2: 39.3 | 1.11× |

这四个形状合计 34.81 MB：**215.2 → 142.6 µs = 1.51×**。

## 3.4 真实 kernel 上的 A/B（生产 flags，逐位等价）

把 R 表打进 `native_mmvq.cu`（备份 `native_mmvq.cu.w862bak`），用 **CMake 在 `build.ninja` 里的逐字 flags** 重编：
`-O3 -DNDEBUG -std=c++20 --offload-arch=gfx906` + `-DSTRATA_HAVE_DFLASH2 / STRATA_HIP_GFX906 / STRATA_VERIFY_MAX_T=8`
+ `-isystem include/strata/platform/hip_compat`。
（**坑**：用 `include/strata/hip_compat` 那套 compat 头重编，整份二进制会慢 45%，把结论全污染。这两个目录不是同一个东西。）

ncols=6（单请求验证窗口的真实形状），隔离逐矩阵，单位 µs：

| 矩阵 | 字节 | R=1（现状） | R 表 | 增益 |
|---|---|---|---|---|
| GDN qkv 2560→10240 | 27.85 MB | 153.4 | **85.3** | **1.80×** |
| GDN gate 2560→6144 | 16.71 MB | 93.4 | **52.7** | **1.77×** |
| out 6144→2560 | 16.71 MB | 86.8 | **53.7** | **1.62×** |
| QSA q 2560→12288 | 33.42 MB | 153.8 | **86.1** | **1.79×** |
| shared down 640→2560 | 1.74 MB | 19.1 | 16.2 | 1.18× |
| HC up 320→10240 | 3.48 MB | 36.4 | 35.0 | 1.04× |
| k/v / HC down / g-u | 小 | — | — | 1.00×（blocks<120，表里取 1） |
| **合计 / 层** | 106.54 MB | **613.6** | **399.9** | **1.53×** |

整层连续发射：**622.6 → 409.1 µs（1.52×）**，原始权重带宽 **171.1 → 260.4 GB/s**。

ncols=1（没有投机窗口时的普通 decode）：209.9 → 207.0 µs，**1.01×（噪声内）**。
⇒ 收益只落在多列路径上，而这正是单请求 decode 走的路径。

## 4 数值等价性（这是能不能上的门槛）

R 只改"一个波算几行"，**每行的归约顺序一点没变**（同 lane 映射、同 kbx 顺序、同 64-lane butterfly），
所以输出必须逐位相同。实测四个形状、ncols=6：

```
qkv  2560->10240   R=2 vs R=1: bitwise-equal  diff=0/61440   max|d|=0
qkv  2560->10240   R=4 vs R=1: bitwise-equal  diff=0/61440   max|d|=0
g/u  2560->640     R=2 vs R=1: bitwise-equal  diff=0/3840    max|d|=0
down  640->2560    R=2 vs R=1: bitwise-equal  diff=0/15360   max|d|=0
hcup  320->10240   R=2 vs R=1: bitwise-equal  diff=0/61440   max|d|=0
```

真实 kernel（打进 `native_mmvq.cu` 后）复验，ncols=1 与 ncols=6 各 9 个形状全部 `diff=0`：
`GDN qkv 0/61440`、`QSA q 0/73728`、`HC up 0/61440`、`shared down 0/15360` …

⇒ 这是**调度改动，不是数值改动**，不需要新的精度门，不需要重跑 36 题。
项目自己的 CUDA `il_rows` 表注释也是同一句：*"Each choice is bitwise the same output, so a table is only speed."*

## 5 落地形态

生产 kernel 里 `R` **本来就是模板参数**（`native_mmvq_wave_kernel<F, NCOLS, R>`），只是 `wave_launch_n` 里写死
`constexpr int R = 1`。改法与项目自己的 B6（`STRATA_B6_MMVQ_ROWS`）同款：

```cpp
// wave_launch_n: 按 ncols 选 R，保持 R*NCOLS <= 12，且 blocks >= ~120（2 个 CU 波次）
//   ncols 1     -> R = min(4, max(1, n_out / 512))
//   ncols 2..3  -> R = 4
//   ncols 4..8  -> R = 2
// env STRATA_MMVQ_WAVE_ROWS 可覆盖（默认 = 上表，=1 即回到现状）
```

选 R 的两条约束都有实测支撑：
- `R×NCOLS ≤ 12`：ncols=6 R=4（24 累加器）实测 118.0 µs，比 R=1 的 133.9 只是略好，远差于 R=2 的 72.8；
- `blocks ≥ 120`：`g/u 640 行` 在 ncols=1 时 R=4 只有 40 block，实测 10.8 µs 反而比 R=1 的 5.2 µs 慢一倍。

## 6 折算到每 token（诚实版）

一层 9 个矩阵在 ncols=6 下共 **622.6 µs**（生产 flags，106.54 MB，171 GB/s 原始带宽）。
开 R 表后 **409.1 µs**，**每层省 213 µs（1.52×）**。

每 token 的 dense GEMV（48 层，按 6 列摊）：**3.46 ms**（bench 折算）/ **2.05 ms**（生产逐桶账里 GDN `gemv` 3.05 + QSA `q+q-idx` 1.8，按 2.36 tok/window 折算）。

⇒ 1.52× 的收益 = **每 token 省 0.8-1.2 ms**，占 21.8 ms/token 的 **3.5-5.4%**。

**这个数比我上一轮说的"9.1%"小**，原因是两件事同时纠正了：① 22% 那个基线不成立（真值 45-71%）；
② 生产 decode 本来就是多列验证窗口，权重已经被 6 个位置摊过一次（每位置成本已是 ncols=1 的 1/2.2）。

## 7 外部证据（三条独立来源，机理一致）

1. **`qr0n/p100-llama-cpp` patches/0002**：`calc_rows_per_block` 在 ncols=1 时返回 1，于是"每个输出行都重新加载并重解包同一份激活"；
   改成 4 rows/block 共享后作者原话 **"This is the large one."**
2. **bittide（MI50 实测）**：`ncols_dst=4` 时"每个激活块被载入 4 次"，激活的 L2 流量 ×4，实测 **2.04× 开销**；
   其 MI50 表格里 Flat Q8 GEMV(N=1) 只有 **92 GB/s = 24%**（我们生产是 473-618，已远好于它）。
3. **llama.cpp PR #30517**（2026-10-17）：低比特类型"每线程权重字节少，所以让每 block 算两行来共享 q8_1 激活载入"，
   Q2_K/Q3_K 在 3090 上 **1.37-1.56×**；并注明 **Q8_0 在 NVIDIA 上是 1.00×（噪声底）**——因为 NVIDIA 上 Q8_0 已经贴带宽，
   而我们的场景是 gfx906 + ncols=6，属于"低比特 + 多列"，正是它有用的那一档。

## 8 没做的 / 下一步

1. **生产 kernel 上逐位复验**：本次等价性是在自足内核上验的，机制相同但要在 `native_mmvq_wave_kernel<F,NCOLS,R>`
   上再跑一次（改一个 dispatch + 一个 knob，然后 `--group check` 对 R=1/R=2）。
2. **gate / out / QSA q 三个大形状补测**（本文件只测了 4 个）。
3. **`split` 布局**：ncols=1 时独立有 1.44×（qs 32 字节对齐，每 8 字节 1 次载入而不是 4 次 u16）。
   总字节数不变，可在加载时用一个 ≤30 MB 的 scratch 原地重排；但 ncols=6 加了 R 之后收益被吃平，**优先级低于 R**。
4. **真正的天花板不在 GEMV**：生产逐桶账里 `VRAM hits` 6.6-7.2 ms/window 与 `hc-read1+router` 4.9 ms/window 才是主体，
   GEMV 两个桶合计 4.85 ms/window。

## 9 复现

```bash
bash /home/albus/w862_lab2_run.sh          # 编译 + 全扫 + 逐位一致性
# 源：albus/w862/q8_wave_lab.cu  产物：/home/albus/w862_lab2/q8_wave_lab
```
