# hipBLASLt on gfx906 (vega20) — 分支说明

> 分支 `gfx906/hipblaslt-vega20`，从 `gfx906/0.2.9-mi50 @ aef9d25` 开出。
> 目的：把「给 gfx906 建 hipBLASLt 后端」这件事**从讨论变成可验证的步骤**。
> 本分支**不影响生产**：生产跑的是 rocBLAS 路径（`STRATA_ROCBLAS_TUNING`，84 行表，平均 gain 3.04×）。

## 1 为什么单开一个分支

hipBLASLt 在 gfx906 上不是「少一张调优表」，而是**库里一个 solution 都没有**（`AlgoGetHeuristic → status=3, algos=0`）。
要做，得改 ROCm 的 TensileLite（kernel 生成器），再改 Strata 的编译门控。这会碰到：

- `STRATA_ENABLE_HIP` 与 `STRATA_HIP_GFX906` 在 `CMakeLists.txt:89` 是 `FATAL_ERROR` 互斥；
- `gemm.cu` 里 400 多行 hipBLASLt 代码由 `STRATA_HIPBLASLT_AVAILABLE` 门控，我们这条构建**从来没编过它**。

把这两件事塞进主线会把「生产调优」的风险面扩大一个数量级。所以：**主线继续走 rocBLAS，hipBLASLt 单开分支试**。

## 2 已知事实（全部实测/源码核实，见 `deploy/W852_HIPBLASLT_SELFBUILD.md`）

| 事实 | 证据 |
|---|---|
| gfx906 不在上游 `SUPPORTED_ARCHITECTURES` | `cmake/tensilelite_supported_architectures.cmake` |
| 但代码「认识」gfx906 | `Common/Architectures.py` 的 `architectureMap` 有 `"gfx906": "vega20"` |
| 没有任何 vega20 的 logic | 上游（TheRock-gfx906 文档直言 `there is no vega20 logic`） |
| TensileLite 生成的 asm 过不了 gfx906 汇编器 | Debian debian-ai 实测：`.amdhsa_accum_offset` — **requires gfx90a+** |
| 我们的构建不编 hipBLASLt | `CMakeLists.txt:848` 要 `STRATA_ENABLE_HIP`，我们是 `STRATA_HIP_GFX906` |
| rocBLAS 那条路有货 | 210 个 `*gfx906*` 内核文件（36 MB），表均 gain 3.04× |

## 3 成功的定义（先写死判据，避免"做了一半说成了"）

**P0（能不能）**：TensileLite 能为 gfx906 生成**至少一个** kernel，并且被 `clang -x assembler` 汇编成 `.hsaco`。
→ 失败点大概率是 `.amdhsa_accum_offset` / `.amdhsa_next_free_vgpr`（MFMA 的累加器布局，gfx90a+ 才有）。

**P1（对不对）**：hipBLASLt 的 `hipblasLtMatmulAlgoGetHeuristic` 在 gfx906 上返回 `algos > 0`，
且 `hipblasLtMatmul` 的输出与 rocBLAS 同形的 FP16 GEMM 对拍通过（`relative_l2 < 1e-3`）。

**P2（快不快）**：与 rocBLAS 的最优解（我们那张 84 行表）在同一组形状上比。
**门槛：至少一个形状比 rocBLAS 表里的解快 5% 以上**，否则这个分支的产出没有意义——
rocBLAS 已经调过 84 个形状，平均 3.04×，hipBLASLt 要赢必须有实据。

**任何一步不过，就停在那一层并记录原因**，不往下堆。

## 4 步骤与每步的验证

| # | 动作 | 验证 | 成本 |
|---|---|---|---|
| 1 | 拉 `rocm-libraries/projects/hipblaslt/tensilelite`（sparse） | 目录里有 `tensilelite/`、`rocisa/`、`cmake/` | 分钟 |
| 2 | 打 `patches/0001-supported-architectures-add-gfx906.patch` | `grep -c gfx906 tensilelite_supported_architectures.cmake` ≥ 1 | 分钟 |
| 3 | 造 vega20 的 logic（**第一道墙**） | `Logic/` 下出现 gfx906 可用的 yaml，或被 `TensileCreateLibrary` 接受 | 天–周 |
| 4 | 跑 codegen：`TensileCreateLibrary --architecture=gfx906` | 产出 `TensileLibrary*.dat` + `.s` | 分钟–小时 |
| 5 | 汇编（**第二道墙**） | `.s` → `.hsaco` 无错；出现 `.amdhsa_accum_offset` 即为墙 | 分钟 |
| 6 | 装进一个候选 hipBLASLt 库目录，跑 `probe_hblt` | `algos > 0` | 分钟 |
| 7 | 数值对拍 | `relative_l2` / `max_abs` 在容差内 | 分钟 |
| 8 | 性能对拍（对 rocBLAS 84 行表） | ≥1 个形状快 5% | 小时 |
| 9 | 若 8 通过：拆 `CMakeLists.txt:89` 的互斥，重编引擎 | `--version` + `hipblasLtMatmulAlgoGetHeuristic` 在引擎日志里出现 | 小时 |
| 10 | 若 9 通过：`tune_hipblaslt` 出表 + ABBA | 与 rocBLAS 路径同口径比 read/decode | 小时 |

## 5 本分支的文件

```
docs/hipblaslt-gfx906/
  PLAN.md                     ← 本文（判据与步骤）
  probe_hblt.cpp              ← 探测 hipBLASLt 有没有可用解（W851 已用它判死过一次）
  probe_tensilelite.sh        ← 步骤 1/2/4/5 的一键判定（P0 探针，2–4 小时）
  patches/
    0001-supported-architectures-add-gfx906.patch
```

## 6 现在的位置

- **P0 未验证**：还没跑过 `TensileCreateLibrary --architecture=gfx906`。
  在跑之前，所有「能做/不能做」都是推断 —— 本分支存在的意义就是把它变成实测。
- 生产**不受影响**：主干 `gfx906/0.2.9-mi50` 继续跑 rocBLAS 路径，ROCm 10.1 + 84 行表。
