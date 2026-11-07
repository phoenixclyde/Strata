# W852 · hipBLASLt 在 gfx906 上：全网找完了，结论是「能建，但要重写一个后端」

> **AUDIT16 补记**：① `THEROCK_ENABLE_HIPBLASLTPROVIDER=OFF` 在原文里的解释是
> "*hipDNN provider on top of hipBLASLt*, which has no gfx906 kernels" —— 它关的是 **hipDNN 的 provider**，
> 不是 hipBLASLt 库本身；本件 §1.1 的措辞按此更正。
> ② §1.3 的两个 issue 正文都不含 gfx906（见 `W851_HIPBLASLT_VERDICT.md` 顶部补记）。
> ③ 第 5 步之后的判据没问题，但注意**同一堵墙也挡着 MMQ**（`CMakeLists.txt:145` 要求 `STRATA_ENABLE_HIP`），
> 见 `AUDIT16_W844_W853.md` P0-4：那里只要放开一个条件就能试，比 hipBLASLt 便宜得多。

> 2026-10-31 23:0x。机主令：「hipBLASLt 继续全网找，不行就是找建起来的办法。自己弄没关系的，只要能弄。」
> 本件把「能不能做」「谁能做」「自己做得付多少」三件事分开写，最后给一个 2–4 小时的判定实验。

## 1 全网找到的四条独立证据（都不是猜的）

### 1.1 社区最大的 gfx906 项目已经替我们把这道题做了两遍

**`Wizard815/TheRock-gfx906`**（专门为 gfx906 从源码建 ROCm 10.x 的项目）在 `GFX906.md` 里直接写：

> hipBLASLt does not support gfx906: upstream excludes it from `tensilelite_supported_architectures.cmake`,
> **there is no vega20 logic**, and TheRock builds the target-neutral hipBLASLt subproject only for gfx1100.
> The resulting install has `lib/rocblas/library/gfx906` but no `lib/hipblaslt/library/gfx906`.
>
> Practical effect: Ordinary FP16/BF16/FP32 GEMMs (llama.cpp, whisper.cpp, PyTorch matmul) go through
> **rocBLAS** and work. Anything that calls hipBLASLt directly fails at heuristic selection.

他们的做法是**关掉**：`-DTHEROCK_ENABLE_HIPBLASLTPROVIDER=OFF`，注释写 `hipBLASLt, which has no gfx906 kernels`。

`mixa3607/ML-gfx906`（★364，gfx906 生态里最全的构建集）有 `rocm-tensile/` 目录（给 **rocBLAS** 跑 Tensile），
**没有** hipBLASLt 的构建 —— 同一个判断。

### 1.2 有人真的试过编译，撞在汇编器上

Debian `debian-ai` 邮件列表（2024-03，给 gfx803 编 hipBLASLt 的记录）：

```
S_8_32_gfx803.s:257:1: error: directive requires gfx90a+   .amdhsa_accum_offset 8
S_8_32_gfx803.s:258:1: error: unknown directive           .amdhsa_next_free_vgpr
```

发信人的结论：

> It's "**lite**" because they've dropped a lot of features, **including hardware compatibility**.
> **This is not a library that we're going to be able to port to other architectures.**

`.amdhsa_accum_offset` 是 **MFMA（matrix core）累加器**的布局指令，gfx90a 起才有。gfx906 没有 MFMA
（只有 V_DOT2/V_DOT4），所以 TensileLite 生成的 asm 在 gfx906 上**过不了汇编器**。

### 1.3 上游把它当"不支持的架构"处理

`ROCm/hipBLASLt#1243` 与 `pytorch#138067` 的标题就是
`Attempting to use hipBLASLt on an unsupported architecture!` —— gfx906 在官方口径里是 unsupported，
PyTorch 的规避办法是把 gfx906 固定回 rocBLAS（`TORCH_BLAS_PREFER_HIPBLASLT=0`）。

### 1.4 我们自己的实测（W851）

两代 ROCm（7.14 / 10.1）都是：

```
Could not load "TensileLibrary_lazy_gfx906.dat"
hipModuleLoad failed: Kernels.so-000-gfx906.hsaco  error: file not found
hipblasLtMatmulAlgoGetHeuristic -> status=3  algos=0
```

## 2 但代码里「认识」gfx906 —— 这是唯一的好消息

上游 `projects/hipblaslt/tensilelite/tensilelite/Common/Architectures.py`：

```python
architectureMap = {
    "all": "_",
    "gfx803": "r9nano",
    "gfx900": "vega10",
    "gfx906": "vega20",        # ← 名字映射是有的
    ...
}
```

`rocisa`（汇编器）的 `include/helper.hpp` 里也命中 `gfx906`。
⇒ **不是「完全不认识」，而是「认识但没为它生成过内核」**。这决定了 §3 的路径存在。

## 3 「自己弄」的完整路径与每一关

| # | 步骤 | 难度 | 备注 |
|---|---|---|---|
| 1 | 拉 `rocm-libraries/projects/hipblaslt/tensilelite` 源码 | 易 | 镜像里只装了 `rocisa` 的 `.so`，**没有 Python 生成器**，必须从源码拉 |
| 2 | `cmake/tensilelite_supported_architectures.cmake` 的 `SUPPORTED_ARCHITECTURES` / `BASE_ARCHITECTURES` 加 `gfx906` | 易 | 1–2 行 |
| 3 | **写 vega20 的 logic（tuning yaml）** | **难** | 上游 `there is no vega20 logic`；rocBLAS 的老 Tensile 有 vega20 logic，但那是 Tensile 不是 TensileLite，格式要转 |
| 4 | 跑 codegen：`TensileCreateLibrary --architecture=gfx906` | 中 | 依赖 Python 环境 + `rocisa`（版本要与源码匹配） |
| 5 | **过汇编器**：生成的 asm 里有 `.amdhsa_accum_offset` / `.amdhsa_next_free_vgpr`（gfx90a+） | **难** | 必须改 asm 生成器，绕开 MFMA 累加器布局，改走 VALU/V_DOT2 —— 这是**改 kernel 模板**，不是改参数 |
| 6 | 用 hipBLASLt API 验证 `AlgoGetHeuristic > 0` + 数值对拍 | 中 | 我们现在就能跑这个探测（`albus/w851/probe_hblt.cpp`） |
| 7 | Strata 侧：`STRATA_ENABLE_HIP` 与 `STRATA_HIP_GFX906` 互斥（`CMakeLists.txt:89` FATAL_ERROR）要拆开，重新编引擎 | 中 | 拆完还要把 `gemm.cu` 那 400 行 hipBLASLt 分支编进来 |
| 8 | 调优表（`tune_hipblaslt`）+ A/B | 中 | 这一步和现在的 rocBLAS 表流程一样 |

**第 3 与第 5 是真正的墙**：一个要造 tuning 空间，一个要改 kernel 生成器。合计按周计，且没有上游保证
（AMD 已经把这代卡从官方矩阵里拿掉了）。

## 4 判词

| 说法 | 对不对 |
|---|---|
| 「hipBLASLt 表做不出来」 | **对**，因为库里一个 solution 都没有（前提不成立） |
| 「自己建不出来」 | **不对**。路径存在（代码认识 gfx906），但那是**重写一个后端**，不是打补丁 |
| 「值不值得」 | **不值得，而且大概率白做**：rocBLAS 已经有 **210 个 gfx906 内核文件**（36 MB `Tensile\*_gfx906.dat` + `Kernels.so-000-gfx906.hsaco`），我们的表在 84 个形状上**平均 gain 3.04×**。hipBLASLt 要赢，得先超过这批已经调过的内核，没有理由认为它能 |

**结论**：不建议投入。如果一定要验，做 §3 的 1、2、4、5 四步 —— **2–4 小时就能知道是不是死路**
（一撞 `.amdhsa_accum_offset` 就说明必须改生成器，成本立刻从"天"跳到"周"）。这个探针不动生产、不占 GPU。

## 5 真正还留在桌上的（比 hipBLASLt 值钱）

W851 的算术已经指出：331-token 的 prefill 里，**14 个 dense GEMM 合计只有 10.5 ms，占 1550 ms 的 0.68%**。
就算把 hipBLASLt 建成、把这 10.5 ms 再砍一半，也只是 0.34%。

那 1540 ms 在别处 —— 按 W804 的记录是 **staging + CPU 侧**。这轮之后该打的是：

1. **M5 `STRATA_PREFILL_TIMING`**（21 个相位现成，不改源码）→ 先把 1.5 s 拆开
2. **R6 roofline 三条**（LDS 隔行 padding / DPP 归约 / fp16 dot2 的微基准，不停服）
3. 10.1 带来的 **hipFile 异步快路**（staging 正是它要解决的事，官方 10.1 release notes 的头条之一）

第 3 条是这轮升级**唯一可能带来真收益**的地方，而且它和老代码路径不冲突 —— 值得排在下一枪。
