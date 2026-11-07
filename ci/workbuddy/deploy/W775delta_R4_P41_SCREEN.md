# W775delta R4 ---- `P41` §4 族 15 开关「本卡可及性」筛选（step-2 成果）

> 做法：只读 **0.1.42 镜像**源码（`docker run --rm`，无 GPU、无停生产）。逐开关取「命中行 + 最近前置 `#if` 守卫」，
> 再核**总开关表** `src/core/arch_defaults.cpp` 与**构建宏**。时间：2026-10-11 12:1x。**未发车。**

## 0 结论（先行）

1. **§4 族在本卡一个都不会自动开**：`arch_default_env()` 只在 **gfx12** 或 **gfx1151** 时返回表；
   `gfx906` 走 `if (!gfx_arch_is_gfx1151(gcn_arch)) return t;`（`t` 为空）=> **空表**。要测必须**显式设 env**。
2. 那张表的**收益注释全是 gfx1151/Aurora 实测**（如 `GDN_PP` "64K prompt +2.9%"、`Q8_PACKED` "decode +2.3%"）
   => register 一直警示的「上游数据取自 gfx1151、不可照搬」**被源码证实**。
3. **`P41` 的 15 个 = 该表 18 项 减去已测已否决的 3 个**（`EXPERT_V2`=P36 / `TSUM`=P37 / `SH_STREAM`=P40）。核对无误。
4. **先排 1 个**：`STRATA_HCD_EXACT`（见 §1.3，机制不支持）。
5. **需前置 1 个**：`STRATA_PF_PAD`（注释逐字 *"acts with `STRATA_PF_GEMM`; inert without it"*）。
6. **候选 13 个**（可及、未测、不在已否决名单）：见 §3。

## 1 源码事实（0.1.42 镜像，逐字）

### 1.1 总开关表 `src/core/arch_defaults.cpp`
```cpp
if (gfx_arch_is_gfx12(gcn_arch)) { ... 5 键 ... }
if (!gfx_arch_is_gfx1151(gcn_arch)) return t;   // <== gfx906 在这里返回空表
...
t = { GDN_HEAD GDN_PP GDN_CONVL2 GDN_NOY CVEC_FUSE HCD_EXACT PF_PAD
      Q8_PACKED Q6_PACKED MMVF_ROWS ATTN_LANECELL EXPERT_V2 TSUM LFUSE GDN_SPLIT QFUSE PLE_BATCH SH_STREAM };
```
- `gfx_arch_is_gfx1151()` = `gfx_arch_is(gcn, "gfx1151")`（`include/strata/kernels/gfx_arch.hpp:33`）=> gfx906 恒假。
- 用户显式设的值**优先**：`if (std::getenv(kv.first.c_str()) != nullptr) continue;` => 我们的臂只需设 env 即可覆盖。
- 生效时会打 banner：`strata: gfx1151 (Strix Halo): N exact speed switches on by default (...)`。

### 1.2 每项的收益出处（表内注释，全部 gfx1151/Aurora）
`GDN_PP` "64K prompt +2.9%" · `GDN_CONVL2` "64K -0.3 s" · `HCD_EXACT` "64K +1.8% (stream S)" ·
`Q8_PACKED` "decode +2.3%" · `LFUSE`/`QFUSE`/`PLE_BATCH` 等标 S25/S26（Aurora 流）。**没有一项标 gfx906。**

### 1.3 `STRATA_HCD_EXACT` ---- **机制不支持，先排**
gfx12 表处的注释逐字：
> *"STRATA_HCD_EXACT is left out: it needs the gfx1151 hipBLASLt tuning table, finds none on gfx12, says so on every
> start and does nothing (measured: with and without it identical, 0.0 to +0.1%)."*
且 `src/prefill/gemm.cu:549` 有守卫 `#if defined(__HIPCC__) && defined(STRATA_HIPBLASLT_AVAILABLE)` + 一行
`STRATA_HCD_EXACT: no hipBLASLt tuning table is loaded, so the exact ke...` => **依赖 gfx1151 专属 tuning table**。
=> 本卡（gfx906）几乎必然同样"no table => does nothing"。**先排**（若仍要测，须先证 hipBLASLt table 存在）。

### 1.4 `STRATA_PF_PAD` ---- **须与 `STRATA_PF_GEMM` 同车**
表内注释逐字：*"padded GEMM row strides (acts with `STRATA_PF_GEMM`; inert without it)"* => 单独设 = **无效**。

### 1.5 `STRATA_GDN_CONVL2` ---- AMD-only（对我们有利）
表内注释逐字：*"it is not bitwise on CUDA 13.3 sm_120 (#1522), and this table is never consulted by a CUDA build."*
=> 我们是 AMD => 该条**适用**。

### 1.6 `STRATA_ATTN_LANECELL` ---- 与 P55 swizzle 互斥
命中在 `src/kernels/cuda/qsa_decode_attn.cu:166/637`（decode attention）；注释 *"bit-identical scores, no shuffl..."*。
而 `use_query_swizzle = query_swizzle && !lane_cell && kv_mode==1 && ...` => **开 LANECELL 会关掉 swizzle 路径**
（P55 在 k8v4 下本已不可达，故实际不冲突；但登记时须知）。

## 2 构建面（0.1.42 实建，`build-ctx-412/build-412.log:92`）

```
cmake -S /src -B /src/build-906 -G Ninja -DSTRATA_HIP_GFX906=ON
      -DCMAKE_HIP_ARCHITECTURES=gfx906 -DSTRATA_GGML_DIR=/src/third_party/llama.cpp
      -DCMAKE_C_COMPILER=/opt/rocm/llvm/bin/clang -DCMAKE_CXX_COMPILER=/opt/rocm/llvm/bin/clang++
      -DSTRATA_MMQ_KQUANTS=ON
```
[!] **更正 `W775delta_W12_PRECHECK.md` §1**：那里记「`-DSTRATA_USE_HIP` **0 处**」；
实读 `src/cmake/hip_backend.cmake:89` = `target_compile_definitions(strata_hip_runtime INTERFACE STRATA_USE_HIP=1 ...)`
=> **`STRATA_USE_HIP=1` 是定义的**（经 INTERFACE 目标传播；`CMakeLists.txt` 里不出现是正常的）。
**这条只影响"哪些块被编进去"的判断**（如 `prefill/gemm.cu` 的 `#ifdef STRATA_USE_HIP`），**不影响 P55/P56 的判决**。 **（2026-10-11 12:3x 收窄：该宏只对链接 `strata_hip_runtime` 的目标生效；主引擎目标不拿它 => 主引擎的 CUDA 分支是活的。见 `deploy/W775delta_RTS_TAILSKIP_FINDING.md` 1-2 节。）**
> 局限：**未逐目标核** `prefill/gemm.cu` 是否链接了 `strata_hip_runtime` => 该宏是否覆盖它，属"高可能、未证"。

## 3 筛选结果

| 处置 | 开关 | 理由 |
|---|---|---|
| **先排** | `STRATA_HCD_EXACT` | §1.3：需 gfx1151 hipBLASLt tuning table；上游在 gfx12 实测 = 无效果 | **[引用精度更正 2026-10-11：该注释位于 `arch_defaults.cpp:17` 的 gfx12 分支；gfx906 侧准确表述为「不在任何 gfx906 表里（表为空）+ 依赖 hipBLASLt 调优表（本卡无）」，「实测 0.0~+0.1%」是 gfx12 的数。见 `W775delta_SRC142_VERIFY.md` §1.2]**
| **需前置** | `STRATA_PF_PAD` | §1.4：须 `STRATA_PF_GEMM=1` |
| **已否决（不在 P41）** | `EXPERT_V2`(=P36) · `TSUM`(=P37) · `SH_STREAM`(=P40) | register 已 REJECTED |
| **候选（13）** | prompt：`GDN_HEAD` · `GDN_PP` · `GDN_CONVL2` · `GDN_NOY` · `CVEC_FUSE`<br>decode：`Q8_PACKED` · `Q6_PACKED` · `MMVF_ROWS` · `ATTN_LANECELL` · `LFUSE` · `GDN_SPLIT` · `QFUSE` · `PLE_BATCH` | 可及、未测、不在已否决名单 |

## 4 建议次序（先 3 个，各自独立发车）

| 优先 | 开关 | 为什么先它 |
|---|---|---|
| 1 | `STRATA_Q8_PACKED` | 上游 gfx1151 "decode +2.3%"；**与我们 pack 直接对口**（`P45` 实读：Q8_0 张量 **303 个**）=> 本卡也吃这条路径 |
| 2 | `STRATA_ATTN_LANECELL` | decode 注意力布局（bit-identical scores）；与已否决族无关；注意 §1.6 的互斥 |
| 3 | `STRATA_GDN_PP=2` | 上游 "64K prompt +2.9%"（prompt 侧量级最大者） |

**纪律**：**同路径不可组合测**（W723）=> 上述每个**单独一车**；每车须照 W12 的老办法先做**零成本可及性确认**
（显式设 env 起一次车，看 banner / 行为变化），再决定是否发正式 A/B 车。

## 5 局限

- 本件**未发车**：结论限于「源码在性 + 总开关表 + 构建宏」。
- 收益数字**全部来自 gfx1151**，本卡**必须实测**（同族已测的两个是负的：`EXPERT_V2` -5.60%）。
- `#if` 守卫取的是**最近前置**预处理行（启发式），不等于严格的外层守卫 => 逐项"编译进没进"仍须逐车确认。
- §2 的 `STRATA_USE_HIP` 覆盖问题未逐目标核（见该节局限）。
