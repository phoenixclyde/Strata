# W901 · R52 wave64 波口径审计：32-lane 是有意契约（实测确认），真正的债是 mask 被丢弃

> 2026-11-03 01:1x。**零停服**：只读源码 + 一个 64 线程微核（`albus/w899/shfl_probe.cu`，跑在空闲的 GPU 上，
> 峰值占用一个 block、1 个波）。生产容器全程未动。

---

## 1 结论先行（三句话）

1. **“全按 WARP=32 记账”不是缺陷，是设计契约**：`include/strata/platform/hip_compat/strata_hip.h` 头注释逐字写明
   「every Strata kernel is written for a 32-lane warp … here a CUDA warp is a **LOGICAL 32-lane half** of a wavefront:
   every shuffle **defaults to width 32**」。**我此前在 `W893` 把这件事写成“漏项/浪费”，是错的，本件更正。**
2. **硬件实测确认该契约成立**：`width=32` 时高半组取到的是**本组** lane 31（=物理 63），`width=64` 才是物理 31。
   所以 `qsa_select` 里那些 `__shfl_sync(0xffffffffu, ps, 31)` **不是 bug**（我一开始怀疑它跨半波取错）。
3. **真正的债是 mask 语义**：垫片把 mask 整个丢掉（`#define __shfl_sync(mask, var, lane, ...) __shfl(var, lane, …)`），
   而 **HIP 7.14 会硬性拒绝 32 位 mask**（`static_assert(sizeof(MaskT) == 8)`，原文见 §3）。也就是说：
   今天能编过**全靠垫片**；任何依赖 mask（发散安全）的新代码在这里都是空操作。

---

## 2 契约与实现（源码逐字）

`strata_hip.h:8-12`：

```
// The warp contract: every Strata kernel is written for a 32-lane warp.  gfx906 runs 64-lane wavefronts, so
// here a CUDA warp is a LOGICAL 32-lane half of a wavefront: every shuffle defaults to width 32 (a
// `__shfl_down_sync(m, v, 1)` at lane 31 must not read lane 32), `__ballot_sync` returns the 32-bit mask of the
// caller's own half, and `__syncwarp` is a wavefront barrier plus an LDS fence.
```

`strata_hip.h:201-207`：

```c
#define __shfl_sync(mask, var, lane, ...) __shfl(var, lane, STRATA_SHFL_W(__VA_ARGS__))
#define STRATA_SHFL_W_GIVEN(w) (w)
#define STRATA_SHFL_W_DEFAULT(...) 32          // ← 不给宽度时就是 32，不是 warpSize(64)
```

---

## 3 硬件实测（`shfl_probe.cu`，gfx906，单 block 64 线程）

```
lane : width32 / width64
 0:31/31   1:31/31  ...  31:31/31
32:63/31  33:63/31  ...  63:63/31      ← 高半组在 width32 下拿到本组的 63
```

⇒ 32-lane 组基址 = `(lane/32)*32`，与 CUDA 语义一致。**归约在组内闭合，不跨半波。**

同一支探针还暴露了工具链事实：用原生 HIP API 写 `__shfl_sync(0xffffffffu, v, 31)` **编不过**：

```
/opt/rocm/core-7.14/include/hip/amd_detail/amd_warp_sync_functions.h:268:62: error:
  static assertion failed due to requirement 'sizeof(unsigned int) == 8':
  The mask must be a 64-bit integer. Implicitly promoting a smaller ...
```

⇒ 生产代码里那 200+ 处 `0xffffffffu` 之所以能编，**唯一原因是 `-isystem …/hip_compat` 把 `__shfl_*_sync` 换成了丢 mask 的宏**。
这条既是**可移植性债**，也是**语义债**：mask 被丢弃意味着“参与集合”不受约束，任何依赖它的发散安全写法都会静默失效。

---

## 4 波槽占用（2400 = 60 CU × 40 波/CU）

| 内核 | 线程/块 | 真实波/块 | 网格（decode 形状） | 波槽 | 占 2400 |
|---|---:|---:|---|---:|---:|
| `native_mmvq` wave（qkv 10240×2560, R=2） | 256 | 4 | 1280 | 5120 | 213%（多轮） |
| bf16 router GEMV（`mmvf_multi`, 512×2560） | 256 | 4 | 512 | **2048** | **85%** |
| GDN megakernel（R54，TH=512） | 512 | 8 | 60 | **480** | **20%** |
| `router_top10_wave_kernel`（T=4） | 64 | **1** | **4** | **4** | **0.17%** |
| `native_router::route`（单 token） | 256 | 4 | **1** | **4** | **0.17%** |
| qsa top-k（`block_topk_*`） | 1024 | 16 | nq=1 | 16 | 0.67% |
| QSA decode attn（chunk 网格） | 256 | 4 | ~16 | 64 | 2.7% |

**两条由此改写的判断**：

- **R50/R36 的 router GEMV 不是占用率问题**：它有 85% 的波槽，60 GB/s 只能从“单层仅 2.62 MB、读放大/延迟”解释，
  不能再用“块太少”解释（这条与 R50 现在的判据一致，但理由要换成带宽/延迟，不是占用）。
- **真正低占用的是选择类内核**：top-10 只有 4 个波（0.17%）、`native_router` 单块、qsa top-k 单块。
  它们必然**被延迟而非带宽支配**，这与 R36 实测「top-10 0.46 ms、router+plan+bell 3.895 ms」互相印证，
  也解释了 R54 的 megakernel（20% 波槽）为什么在 T≤3 反而更慢。

---

## 5 判定

- **无缺陷**：没有找到跨半波取错的归约；32-lane 归约的每一处都满足 `off ≤ 31` 或显式 `width=32`，
  需要整波归约的地方（`native_mmvq`、`fused_gr`、`router_top10`、`iq_kernels`、megakernel）都显式写了 `64`。
- **R52 结项（DONE）**，产出是：①更正 `W893` 的错误框架；②把 mask 债写成硬证据；
  ③给出波槽表并改写 R50/R36 的解释路径（带宽/延迟，不是占用）。
- **不做代码改动**：mask 债要修就得把 200+ 处 `0xffffffffu` 换成 `0xffffffffffffffffull` 并删除垫片宏，
  属于跨工具链的可移植性工程，**没有实测收益**，不进队列；如果将来升级 HIP，先跑这条编译探针即可预知。

---

## 6 复现

```bash
# 波槽表（源码）
grep -n '<<<' src/kernels/cuda/{native_mmvq,router_top10,native_router,qsa_decode_attn,qsa_select}.cu
# 宽度语义（硬件）
/opt/rocm/llvm/bin/clang++ -x hip -O2 --offload-arch=gfx906 shfl_probe.cu -o shfl_probe
HSA_OVERRIDE_GFX_VERSION=9.0.6 ./shfl_probe
```
