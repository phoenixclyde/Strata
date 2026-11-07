# W899 · R54：megakernel 移植后**逐位相等**（T=1…8 全 0 差异），但收益只在 T≥4，必须按 n 门控

> **本件 §2/§3 的 parity 结论已由 §7 覆盖**：根因是 32-lane 组 vs 64-lane 波，改 `gemv_q80_body` 后
> 全部形状逐位相同。**性能结论也从「−12.7%」修正为「T≥4 才是正收益」**。

> 2026-11-02 23:3x。**生产零改动**（二进制、config、容器都没动）；所有工作在独立 worktree
> `/home/albus/strata166/work/r54`（分支 `r54-port`，基于 `d963c791`）。

---

## 1 做了什么

| 步骤 | 动作 | 结果 |
|---|---|---|
| 1 | 从 `nicejunjie/Strata-rdna3@021ecb8` 取三个文件：`include/strata/kernels/megakernel.hpp`(62)、`src/kernels/cuda/megakernel_gdn.cu`(564)、`src/kernels/mk_gdn_parity.cpp`(217) | 放入 worktree，未并入主线 |
| 2 | 用 `build.ninja` 里 `native_mmvq.cu` 的**逐字 flags** 编译 `megakernel_gdn.cu` | **1 个真错误**（重复 16 次）：`cudaOccupancyMaxActiveBlocksPerMultiprocessor` 未定义 |
| 3 | 定位：该行在 `#if defined(STRATA_USE_HIP)` 的另一支。本树**不定义** `STRATA_USE_HIP`（那 28 个死块就是它），因此走了 CUDA 分支 | 给**这个 TU**加 `-DSTRATA_USE_HIP=1` |
| 4 | 重编 | **rc=0，obj 1,038,496 B，0 error**（只剩 6 类 warning：符号比较、未用变量、nodiscard） |
| 5 | 编 `mk_gdn_parity.cpp` | **rc=0，0 error** |
| 6 | 链接：`clang++ --hip-link` + `libstrata_kernels.a` + `libstrata_core.a` + `-lamdhip64` | **rc=0，12.1 MB 可执行** |
| 7 | 运行 | 见 §2 |

> **不要全树加 `STRATA_USE_HIP`**：`generate.cpp` 里有 28 个 `#if defined(STRATA_USE_HIP)` 死块，
> 全树定义会一次性把它们全部激活。必须 **per-TU**。

## 2 运行结果（gfx906，T=4，L=4，grid=60）

```
layer 0: megakernel done
layer 0: diffs xq 0  qkv 14220  z 8571  h 14213  gate 0  beta 0  y 10793  yq 1  bo 7988
...
parity: DIFFERENT (220746 differing values over 4 layers, T=4, grid 60)
six kernels (the window's)     163.61 us a layer (4 layers a graph, 200 replays)
persistent kernel              142.89 us a layer (4 layers a graph, 200 replays)
saving 20.72 us a layer (12.7%); x36 GDN layers = 0.75 ms a window
```

**两面读**：
- **性能是真的**：GDN 整链 **163.61 → 142.89 µs/层（−12.7%）**，按 36 个 GDN 层折 **0.75 ms/窗口**。
- **结果是错的**：22 万个值不同。但**差异分布给了根因**——`xq`（q8_1 量化）**0 差**、`gate`/`beta` **0 差**，
  而 `qkv`(69%)、`z`(70%)、`h`、`y`(88%)、`bo`(78%) 全差 ⇒ **错在 Q8_0 投影矩阵乘，不在量化、不在 a/b 与步进**。

## 3 根因（源码级）

| 侧 | 实现 | 行/波 |
|---|---|---|
| megakernel | 自带 `gemv_q80_body<NCOLS, MAP>`（`megakernel_gdn.cu:91`），`TH=256` 线程、`blockIdx.x → 8 行/块` | **固定 8 行/块** |
| 生产路径 | `native_mmvq(8, …)` → `wave_rows_for(ncols, n_in, n_out)`（`native_mmvq.cu:2382`，R23 的实测行数表） | **按形状查表**（2/4/8 可变） |

两边**乘的东西一样，分块不一样** ⇒ 归约树不同 ⇒ FP 舍入不同。这正是 `xq`/`gate`/`beta` 干净、只有投影脏的原因。

## 4 下一步（两选一，必须选前者才能过 R54 的逐位门）

- **A（推荐，逐位）**：把 `gemv_q80_body` 的「行/块」参数化，从 `mk_gdn_dense` 里按
  `wave_rows_for(ncols, n_in, n_out)` 传入，使分块与生产一致 ⇒ 应当逐位相同。工作量集中在
  `gemv_q80_body` 的 warp→row 映射与它内部的 `__shfl` 归约宽度（wave64 上还要按 64 lane 复核）。
- **B（不推荐）**：保留 8 行/块，把 parity 门降级为 KL / top-k 一致。代价：窗口的数值从此与生产路径不同，
  必须补 KL 门（现成工具有 `STRATA_LOGPOS`），且 R54 的「逐位」判据失效。

## 5 运行约束（下次别再踩）

- 生产常驻 **33.35/34.34 GB**，只剩约 0.83 GiB。parity 默认 **L=36**（约 1.2 GB）会 **OOM**；
  用 `STRATA_MK_L=4`（约 136 MB）可跑。要在 L=36 上跑 parity，必须先停生产（约 245 s 载入）。
- 诊断计数器一栏全 0（`done/next/entered` 都是 0）⇒ 该诊断路径在当前配置下没接上，**只影响可观测性，不影响结果**（记 P2）。

## 6 复现

```bash
cd /home/albus/strata166/work/r54
F='-x hip -O3 -DNDEBUG -std=c++20 --offload-arch=gfx906 -DSTRATA_USE_HIP=1 -DSTRATA_HAVE_DFLASH2=1 \
   -DSTRATA_HIP_GFX906=1 -DSTRATA_VERIFY_MAX_T=8 -D__HIP_PLATFORM_AMD__=1 -D__HIP_ROCclr__=1 \
   -I./third_party/ggml -I./include -isystem ./include/strata/platform/hip_compat -isystem /opt/rocm/include'
/opt/rocm/llvm/bin/clang++ $F -c src/kernels/cuda/megakernel_gdn.cu -o /tmp/mk.o
/opt/rocm/llvm/bin/clang++ $F -c src/kernels/mk_gdn_parity.cpp -o /tmp/mkp.o
/opt/rocm/llvm/bin/clang++ --hip-link --offload-arch=gfx906 /tmp/mkp.o /tmp/mk.o \
  -L/home/albus/strata166/gfx029-build -lstrata_kernels -lstrata_core -lamdhip64 -o /tmp/mk_parity
HSA_OVERRIDE_GFX_VERSION=9.0.6 STRATA_MK_L=4 STRATA_MK_T=4 /tmp/mk_parity
```

---

## 7 第二相：wave64 归约修复（本节覆盖 §2/§3 的 parity 结论）

### 7.1 根因（源码逐行核对，不是推断）

| 项 | 生产 `native_mmvq_wave_kernel<F,8,R>` | RDNA3 `gemv_q80_body`（原样） |
|---|---|---|
| 行归属 | `lane = tid & 63`，`row0 = (blockIdx*4 + tid>>6) * R` | `lane = vtid & 31`，`row = vb*8 + vtid/32` |
| K 划分 | `kbx = lane / T`，步长 `64 / T` = **16** | `tid = lane + g*32`（4 组），步长 `BPI = 32` |
| 累加器 | 每列 **1 个** | 每 lane **4 个**，先横向相加 |
| 归约 | 64-lane 蝶形（offset 32→1） | `warp_sum`（**32**-lane，offset 16→1） |
| 乘加表达式 | `r.d0 * d1 * float(sumi)` | **完全相同** |

⇒ 乘积集合、缩放顺序都一致，**只有归约树不同**，所以差异只落在 qkv/z 及其下游（h/y/bo），
而 xq/gate/beta 为 0——与 §2 的观测完全吻合。

### 7.2 改动

`src/kernels/cuda/megakernel_gdn.cu` 的 `gemv_q80_body` 重写为 wave64：

- `lane = vtid & 63`、`row0 = (vb*4 + vtid>>6) * R`、`kbx = lane/T` 步长 `64/T`；
- 每列 1 个累加器，`tmp[NCOLS][R]`，`+= F::apply(...)`（调用同一个 trait，表达式不改）；
- 末尾 64-lane 蝶形 `__shfl_xor(v, off, 64)`；
- `R = 2`：4 波 × 2 行 = **8 行/256 线程虚拟块**，与启动器已有的 `n_out/8` 网格完全对齐，
  也正是 `kWaveRows` 在 8 列时给 qkv/z/out 的值（2）。
- **每行求和与 R 无关**（起始 `lane/T`、步长 16 都不含 R），所以表里换成别的 R 仍然逐位。

补丁与产物：`albus/w899/patch_gemv_wave64.py`、`albus/w899/megakernel_gdn.cu`、`albus/w899/build_mk.sh`。

### 7.3 结果一：逐位相等（全形状）

```
parity: BITWISE EQUAL (0 differing values over 4 layers, T=1, grid 60)
parity: BITWISE EQUAL (0 differing values over 4 layers, T=2, grid 60)
parity: BITWISE EQUAL (0 differing values over 4 layers, T=3, grid 60)
parity: BITWISE EQUAL (0 differing values over 4 layers, T=4, grid 60)
parity: BITWISE EQUAL (0 differing values over 4 layers, T=5, grid 60)
parity: BITWISE EQUAL (0 differing values over 4 layers, T=6, grid 60)
parity: BITWISE EQUAL (0 differing values over 4 layers, T=8, grid 60)
```

每层的 `xq / qkv / z / h / gate / beta / y / yq / bo` **逐项 0 差异**。

### 7.4 结果二：收益随 T 翻转（这是关键）

| T | 六内核（生产形态） | 常驻 megakernel | 差 |
|---:|---:|---:|---:|
| 1 | 85.81 µs/层 | 95.12 | **−10.9%（更慢）** |
| 2 | 101.31 | 111.00 | **−9.6%** |
| 3 | 124.51 | 125.59 | −0.9%（打平） |
| 4 | 164.14 | 143.36 | **+12.7%** |
| 5 | 191.84 | 162.95 | **+15.1%** |
| 6 | 217.67 | 181.55 | **+16.6%** |
| 8 | 259.82 | 231.15 | **+11.0%** |

**原因**：常驻核把整层压成 60 个块（1 块/CU），小 T 时并行度不够，阶段屏障的等待摊不掉；
大 T 时省下的 6 次 launch 与阶段间同步才占上风。

**网格不能放大**：`STRATA_MK_GRID=120/480` 直接**挂死**（跨块屏障要求所有块共驻；TH=512 时
只有 1 块/CU）。⇒ 小 T 的劣势**不能**靠加块解决，只能按 T 门控。

### 7.5 与生产的对应关系（决定了门控值）

- 生产的 GDN 有两条路：**T=1** 走 `layer.cpp` 的 `gemv_quantized`（Q8_0 三平面）；**多 token** 走
  `verify.cpp` 的 `native_mmvq(native_type=8, native_data, xq_, …)` + `gdn_conv_ab_multi` /
  `gdn_step_norm_multi`。megakernel 镜像的正是**后一条**。
- 生产日志：`strata decode timing: 43 windows, avg T 3.63, 3.53 tokens/window`（spec 5，接受 ~37/38）
  ⇒ 验证窗集中在 **T=3~4**，正好压在打平点上。
- GDN 链约占窗口 14–16%（W873）⇒ 期望 **+0.9% ~ +1.9%** 窗口，最差 −0.3%。

**判据（写死）**：只在 `n ≥ 4` 且 `!batch_rec_ && !side_proj && !br && !prof_on_` 时启用；
`n ≤ 3` 保持六内核。env 门 `STRATA_MK_GDN`，默认关，回滚=删 env。

### 7.6 下一相（集成，仍在 `r54-port`）

`verify.cpp` 的多 token GDN 段按 `MkGdnArgs` 逐字段映射：

| 字段 | 生产来源 |
|---|---|
| `x` / `xq` | 层输入 `xm` / `xq_`（`q8_attn` 时用 `diag|=32` 跳过 phase 0） |
| `w_qkv` / `w_z` / `w_out` | `wqkv->native_data` / `wg->native_data` / `wo->native_data`（native_type 8） |
| `qkv` / `z` / `h` / `gate` / `beta` / `y` / `bo` | `qkv + tb*C` / `z_ + tb*ZV` / `hb + tb*C` / `gate + tb*HV` / `beta + tb*HV` / `y_ + tb*ZV` / 输出目标 |
| `hist` / `state` | `conv`（`sx.gdn_state` 的 history 段）/ `state` |
| `w_conv` / `w_alpha` / `w_beta` / `dt` / `ssm_a` / `gamma` | `wc->data` / `wa->data` / `wb->data` / `wdt->data` / `wsa->data` / `wnm->data` |
| `counters` | `mk_counters_alloc()`，进程内只分配一次 |

集成后先跑 `ci/bench_pair.py --n 3`：decode 中位不得劣化 >1×CV（单流口径的收工门），
再按 `STRATA_DECODE_TIMING` 看 GDN 相位是否真的下降。

## 8 复现（第二相）

```bash
cd /home/albus/strata166/work/r54 && bash build_mk.sh
for T in 1 4 8; do HSA_OVERRIDE_GFX_VERSION=9.0.6 STRATA_MK_L=4 STRATA_MK_T=$T /tmp/mk_parity64; done
```

### 7.7 集成（已打补丁并编译通过，尚未整机建镜像）

`src/core/verify.cpp` 的 GDN 段已按前表接入，**9 个锚点先断言唯一再改**（`albus/w899/patch_verify_mk.py`）：

| 位置 | 改动 |
|---|---|
| include | 加 `strata/kernels/megakernel.hpp` |
| 段首 | 建 `MkGdnArgs` 并 `mk_gdn_dense(mk, n, cs)`；门 `mk_on` |
| 量化 | `if (!mk_on && !q8_attn) quant_in(...)` |
| qkv / z / out 投影 | 各自 `if (!mk_on && …)` |
| conv / ab / step_norm | 三个分支加 `mk_on`（conv 用空 `if (mk_on) {} else`，step 用 `else if (!mk_on)`） |
| y 的 q8_1 | `if (!mk_on && (!g_qfuse() \|\| batch_rec_)) quant_in(...)`（megakernel 自己写 `xq_`） |

门（写死在代码里）：

```cpp
mk_env && n >= 4 && tb == 0 && te == n && !batch_rec_ && !side_proj && !br && !sidem && !prof_on_
```

`mk_env` = `STRATA_MK_GDN`，**默认关**；回滚 = 删 env（代码路径回到六内核，逐位不变）。

**编译验证**：用 `build.ninja` 里 `verify.cpp` 的逐字 `DEFINES/FLAGS` 单编该 TU ⇒
`verify_rc=0 errors=0`，obj 490,240 B（`albus/w899/build_verify.sh`）。

**还没做的（必须做，不能算完成）**：整机链接与 A/B。宿主机**没有 ninja/cmake**，六个构建目录
全部 `CMAKE_HOME_DIRECTORY=/src`（容器内构建）⇒ 只能走 `build-ctx/Dockerfile` 重建镜像，
再在独占 GPU 的时间窗里跑 `ci/bench_pair.py --n 3`（`STRATA_MK_GDN=1` vs 不设）并读
`STRATA_DECODE_TIMING` 的 GDN 相位。**在此之前 R54 不得进生产。**

### 7.8 这一轮的判断（避免下一轮重复推理）

- 逐位门**已过**，所以剩下的是**工程门**（建镜像 + A/B），不是正确性门。
- 收益上限不高（窗口 +0.9~1.9%），但**零质量风险**、回滚只删 env；它排在 `R52` 之后、`R55` 之前。
- 若 A/B 显示 GDN 相位没有下降（可能被 `adapt wait` 或专家读吞掉），按判据**直接关项**，
  不再改内核 —— 因为逐位与内核级 −12.7% 都已经证明过了，再改只能改窗口结构。

### 7.9 端到端 A/B：A 臂可用，B 臂在启动预热就退出（根因已定，引擎自己报的）

**做法**：不改生产镜像/二进制。把重链产物放 `/data/bin/strata-r54`（md5 `6ddb8367…`，41,733,744 B），
生成两份只差一个 env 的配置 `strata-r54-a.json` / `-b.json`（`exe` 指向新二进制，`log` 各自独立，
b 的 `env` 多一条 `STRATA_MK_GDN=1`），停生产后用同一镜像、同一挂载/设备起测试容器。

| 臂 | 结果 |
|---|---|
| **A（新二进制，env 关）** | 正常：启动 250 s，`/health ok`，日志 462 行、17 次请求；**prefill TTFT 中位 9.088 s（CV 1.9%，≈710 tok/s）**、decode 中位 **68.94 tok/s（CV 16%）**、窗口 **51.02 / 48.80 ms**（avg T 3.78） |
| **B（同一二进制 + `STRATA_MK_GDN=1`）** | **启动预热即退出**：日志 227 行停住，GPU 占用 0%，请求挂死；日志三处 `mk_gdn_dense: invalid arguments`（第 74/142/210 行） |

**根因（引擎自己打印的，不是推断）**：那三行来自 `mk_gdn_dense` 的入参校验
`if (n_tok < 1 || n_tok > 8 || a.counters == nullptr)`。`n_tok` 是 4，落在 1..8 内 ⇒
**`a.counters == nullptr`**，即 `mk_counters_alloc()` 返回了空 —— 它做的是 `cudaMalloc`，
而这段代码运行在 **`cudaStreamBeginCapture(cs_)` 的捕获区里**
（`src/core/verify.cpp:2648 / 2800 / 3795 / 3838` 四处捕获），**捕获期间不允许主机侧分配**，
于是返回错误、`mk_counters_alloc` 返回 null，`mk_gdn_dense` 直接 `std::exit(1)`。

**A 臂的附带价值**：重链后的二进制能正常载入并跑完 17 次请求 ⇒ **“换对象重链”这条路是通的**，
下次只需在代码上补两处即可再测：

1. **计数器在捕获外分配**（`Verifier` 构造/reset 时分配一次，或首次非捕获调用时分配），并把指针传进来；
2. **零化改成捕获内合法的方式**：megakernel 最后一块退出时本就会把计数器清零（头注释逐字
   “no memset: the kernel's last block zeroes the counters on the way out”），
   因此 `mk_gdn_dense` 里那次 `cudaMemset` 应改为 `cudaMemsetAsync(..., cs)` 或直接删掉；
3. **失败要降级不要退出**：`mk_gdn_dense` 在 `counters == nullptr` 时应返回错误码，
   让调用方回落到六内核（本次正是 `std::exit(1)` 把引擎整死，才表现为“启动卡住”）。

**生产已恢复**：`strata166-407` 重新拉起（185 s 就绪，`/health ok`），引擎/config md5 未变；
测试容器已删；`/data/bin/strata-r54` 与两份配置留在盘上供下一轮复用。

**判据不变**：修好上述三点后重跑 A/B；`bench_pair` decode 中位劣化 >1×CV 即回滚。

### 7.10 第二轮 A/B（修好捕获后）：不优于基线，R54 在生产无收益 ⇒ 关闭

修掉 §7.9 的三点后重建重链二进制（41,733,704 B，`strata 0.1.55`），两臂**同一二进制**，只差
`STRATA_MK_GDN`；每臂一次重启，`bench_pair --n 4` + 确定性文本探针（`ci/mk_ab_probe.py`）。

| 指标 | A（env 关） | B（`STRATA_MK_GDN=1`） |
|---|---|---|
| prefill TTFT 中位 | **9.072 s**（CV 0.8%） | 9.092 s（CV 1.4%） |
| decode 中位 | **72.40 tok/s**（CV 13.3%） | 66.77 tok/s（CV 15.5%） |
| 窗口 | **49.18 / 46.71 ms**（avg T 3.69） | 49.63 / 52.51 ms（avg T 2.80 / 3.29） |
| 探针 TOTAL sha | `34ff51c7…` | `34ff51c7…`（**逐字相同**，含同样两条空回答 ⇒ 空文本是探针/模型行为，不是内核） |
| 启动 | 255 s | 250 s，无 `invalid arguments` |

**判定**：B 的窗口**更贵**（均值 51.1 ms vs 47.9 ms）却**产出更少 token**（2.8–3.3 vs 3.69/窗口）
⇒ 与微基准的方向一致（T=1 −10.9%、T=2 −9.6%、T=3 −0.9%）。生产验证窗 **avg T 2.8–3.7**，
`n≥4` 的窗口是少数，能触发的那些也没看到窗口时间下降。

**R54 = DONE_NEG（生产无收益）**，但**不是白做**：

1. **内核级结论成立且可复用**：wave64 `gemv_q80_body` 与生产 **T=1…8 全形状逐位相等**，
   T=4/5/6/8 快 **+12.7% / +15.1% / +16.6% / +11.0%**；将来若把验证窗做大（更多 draft token）
   或做批量/多流，这块直接可用（分支 `r54-port`，env 门默认关）。
2. **工程结论**：常驻核的跨块相位屏障要求**整网格共驻**，而本引擎的窗口是 **`cudaStreamBeginCapture`
   捕获 + 图重放**，捕获期禁止主机侧分配 —— `mk_counters_alloc()` 的 `cudaMalloc` 因此返回空，
   原实现又 `std::exit(1)`，表现为“启动卡住、GPU 0%、请求挂死”。这条对任何“常驻核 + 图捕获”的
   改造都适用：**计数器/scratch 必须在 `Verifier::init` 里分配，且失败只能降级不能退出**。
3. **构建结论**：“换对象重链”可用 —— 复用 `gfx029-build` 副本，在现成镜像里编译两个 TU、
   `ar r` 替换归档成员、跑 `ninja -t commands strata` 的链接行，6 分钟出二进制，不依赖整镜像重建。

**收尾**：生产 `strata166-407` 已恢复（230 s 就绪，`/health ok`，引擎/config md5 未变，restarts=0）；
测试容器已删；`/data/bin/strata-r54` 与两份配置留在盘上（默认不会被任何生产路径引用）。

### 7.11 质疑核查：代码**确实生效**，但“端到端等价”无法证明；§7.10 的文本一致性结论**撤回**

用户的质疑（“你的代码真起作用了吗，会不会写错了”）是对的，我照它做了两件事：

**一、给门加自证（`R54 gate:` / `R54 calls=` 诊断，已重建）**

B 臂日志逐字：

```
R54 gate: n=4 tb=0 te=4 batch=0 side_proj=0 br=0 sidem=0 prof=0 cnt=0x7c80299fb000 on=1
```

A 臂同一行 `on=0`、`cnt` 同样非空 ⇒ **门条件全部成立、计数器在 `Verifier::init` 分配成功、`mk_gdn_dense` 真的被调用**。
`R54 calls=` 不打印是**正常现象**：窗口经 `cudaStreamBeginCapture` 录制后重放，主机代码不再执行，
只有内核在图里跑 —— 这条也解释了为什么只能在捕获那一次看到 gate 行。

**二、用 200 token 长输出比 A/B，结果反而暴露了我上一轮的错误**

| 运行 | TOTAL sha | 长度 |
|---|---|---|
| A（env 关）第 1 次 | `7db7ad51…` | 862 / 855 |
| A（env 关）**第 2 次** | `9c3ddade…` | 835 / 867 |
| B（`MK_GDN=1`） | `62fdbf33…` | 845 / 872 |

**同一配置、同一 prompt、`temperature=0` 的两次 A 就不一样** ⇒ 这台引擎**run 间不确定**
（MTP 草稿抽样、自适应专家/线程调度都会改路径），因此**长文本哈希不能作为 A/B 等价判据**。
相应地，§7.10 里“两臂 TOTAL sha 相同 ⇒ 无正确性差异”这句**撤回**：那次只有 48 token、且两条回答是空串，
属于弱证据，不能支撑结论。

**于是现在的真实状态**：

1. **代码生效**：这一点已被引擎自己的日志证明。
2. **等价性只有独立 parity 支撑**（`mk_gdn_parity`：T=1…8、逐张量 0 差异），但它用的是**自己的缓冲**，
   覆盖不到生产的三处映射风险：`hist` 的 (C, d_conv-1) 布局、`h_k/h_v` 语义、`xq_` 与 `yq` 复用同一块。
   这三处在生产里**从未被逐位验证过**。
3. **收益仍为负/无**：§7.10 的窗口时间（51.1 vs 47.9 ms）在 run 间抖动下也不算强证据，
   但结合微基准（T≤3 一律更慢）与 `avg T 2.8–3.7`，方向是一致的。

**结论不变、但理由更硬**：R54 = **DONE_NEG**，两条独立理由 —— ①生产窗口以 T≤3 为主，赚不到；
②**无法在生产内证明等价**，而未证明等价的加速不许上线。

**若将来真要复活它**，第一步不是调优，而是加一道 in-situ 自检（env 门，只跑前 N 个窗口）：
同一窗口先跑六内核、再跑 megakernel，把 `qkv/z/h/gate/beta/y/bo` 拷回主机逐字节比，打印首个失配偏移。
只有它 0 差异，才谈得上收益。

### 7.12 三处映射逐个核对：**没有证据表明写错**（§7.11 的“未验证”要收窄）

§7.11 说“生产三处映射未验证”，逐条查完源码后这句要收窄——**两处是逐字相同，其余由 parity 覆盖**：

| 映射 | 生产 | megakernel | 判定 |
|---|---|---|---|
| conv 历史 `hist` | 提交核 `hist[c * 3 + src]`（`gdn_conv_commit_kernel`） | `conv_body: hist[c * 3 + src]` | **逐字相同** |
| `ab` 行映射 | `row = bx*2 + (threadIdx.x >> 5)`，`is_beta = row >= h_v`，权重 `wa/wb + r*n` | 同结构 | **逐字相同** |
| `gate/beta` 落位 | `gate[t*h_v + r]` / `beta[t*h_v + r]` | `beta[t*h_v + r]` / `gate[t*h_v + r]` | **相同** |
| `state` 布局 / `h/y` 落位 | 由 `gdn_step_norm_multi(...)` 真实核消费 | — | **由 parity 证明**：`mk_gdn_parity` 传的正是生产函数与生产缓冲，逐张量 0 差异 |
| `qkv/z` 落位 | `native_mmvq` 写 `y[j*n_out + row]` | 同式 | **由 parity 证明**（parity 用的就是 `native_mmvq`） |
| `xq_` ↔ `yq` 复用 | 生产同样把 y 的 q8_1 写进 `xq_` 再给 out 投影读 | `mk.yq = xq_` | **同一约定** |

换句话说：parity 不是“只测了自己的缓冲”，它调用的就是**生产的六个函数**，所以除“参数值”外，
缓冲布局的一致性是被它覆盖的；参数值（N/C/ZV/HK/HV/eps）在生产与 harness 里都来自同一个模型几何。

**仍然没被覆盖的，只有一件事**：整条链在**真实窗口**里跑出来的 `qkv/z/h/gate/beta/y/bo` 与六内核
是否逐字节相同。这一条只能靠 in-situ 双跑自检（§7.11 末尾的方案），**不建议再用文本哈希代替** ——
本引擎同一配置连跑两次文本都不同（`7db7ad51…` vs `9c3ddade…`）。

**所以最终表述**：R54 的**内核等价有据（独立 parity + 布局逐条对得住）**，但**生产内等价未做**；
而 R54 被关的真正理由是**收益**（`avg T 2.8–3.7`，T≤3 一律更慢），不是怀疑写错。
