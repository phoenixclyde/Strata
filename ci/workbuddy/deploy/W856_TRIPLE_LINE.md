# W856 · 三线并行：R16 撤回、hipBLASLt P0 判 BLOCK、R17 诊断支线就绪

> ✅ **状态回填（AUDIT17 P1-2，2026-11-01 15:2x 由 W863 补）**：本件 §2 的「hipBLASLt P0 = **BLOCK**（rocisa 版本错配，codegen 起不来）」
> **已被 W858 §1 解掉**：rocisa 从源码装、五层依赖全打通、gfx906 的 hsaco 已产出。
> 之后 W861 又把整条 B 线跑到终局（`algos` 恒 0，根因是 TensileLite 把 non-MI 守卫拆了）⇒ 结论见 `W861_HIPBLASLT_GFX906.md`。
> 读本件时请以本条为准，不要停在「BLOCK」。

> 2026-11-01 00:2x–00:5x。机主令：「双线走，hipBLASLt 支线同步推，然后同步推另外一条支线，按方案走。你继续下一枪。」
> **本轮没有动生产**（无重启、无换二进制）。

## 0 一句话

| 线 | 结果 |
|---|---|
| 主线「下一枪」 | **R16 撤回**：我把 CMake **选项**当成了编译**定义**。MMQ 一直编着且默认开（`build.ninja` 里 `-DSTRATA_PREFILL_MMQ=1`）。AUDIT16 P0-4 作废，误判复盘写在 `AUDIT16 §11` |
| 支线 1（hipBLASLt） | **P0 = BLOCK（依赖版本错配）**，不是 WALL。分支 `gfx906/hipblaslt-vega20 @ d9d6ab8b` 已推；结论与复现步骤入库 `docs/hipblaslt-gfx906/P0_RESULT.md` |
| 支线 2（R17 诊断） | 新分支 **`gfx906/mmq-plan-banner @ ec368906`**：给 `mmq_plan()` 加一行无条件 banner（MMQ / fused / FP16 各几层）。**已编译通过**（`gfx-mmq-build/strata`，md5 `a10af384…`），未部署 |

## 1 R16 为什么撤回（三条硬证据）

1. `gfx029-build/build.ninja` 里 `strata_prefill` 的编译行含 `-DSTRATA_PREFILL_MMQ=1`
   —— 来自 `CMakeLists.txt:2317`（`if(STRATA_ENABLE_CUDA)` 分支内），而 `STRATA_HIP_GFX906=ON`
   会在 `:91-93` 强制 `STRATA_ENABLE_CUDA=ON`。
2. CMake **选项** `STRATA_PREFILL_MMQ`（`:94`，默认 OFF）只管 `:145` 的合法性检查和 `:2392` 的
   `elseif` 备用分支；选项 OFF ≠ 定义缺席。12 个 cache 的 `OFF` 什么也证明不了。
3. 我引用的"近三次启动 0 条 MMQ 派发行"无效：`MMQ tile` 这条打印来自 W795 的补丁镜像，
   当前源码里没有（`grep -rn 'MMQ tile' src/prefill` = 0）。

⇒ **P112 的 `REJECTED(value=0)`＝"保留 MMQ"与二进制一致**，账本没错，是我读错了层。
新纪律（`AUDIT16 §11`）：判"某功能在不在二进制里"只认 ①编译行的 `-D` ②该功能的独有符号/字符串
③无条件打印的横幅；**不认** CMake 选项、cache 变量、条件打印的缺失。

## 2 hipBLASLt 支线 P0（BLOCK，不是 WALL）

| 事实 | 值 |
|---|---|
| codegen 是否需要 GPU | **不需要**（上游 `GPU-MOCK.md`：`TensileCreateLibrary` 是"host `amdclang++` 的交叉编译"）⇒ P0/P1 全程不碰生产 |
| 镜像里的 rocisa | **只有原生扩展**（`_rocisa.abi3.so`、`libstinkytofu.so`），**没有 Python 包**；`import Tensile` 失败 |
| `develop` 源码 | 要 `VCndMaskB16` → 镜像里的 rocisa 没有 |
| `therock-10.1` 源码 | 要 `SAtomicCmpswapX2` → 镜像里的 rocisa 没有（只有 `Buffer/FlatAtomicCmpswap*`） |
| 结论 | 镜像是 **10.1 的预发布快照**，与两个 ref 都不匹配 ⇒ codegen 起不来（BLOCK） |

**结构性判断（比依赖问题重要）**：墙在 **vega20 logic**，不在 ISA——
`SUPPORTED_ARCHITECTURES` 里同时有 gfx1100/1200 这类**非 MFMA** 目标，说明生成器有非 MFMA 路径；
Debian 那次 `.amdhsa_accum_offset` 是 gfx803 老 `Tensile` 的记录，不能外推到 gfx906。

**下一步**：先在可写目录按同一 ref 构建 rocisa（`pip install ./rocisa`，需先装 pybind11/scikit-build-core/cmake/ninja），
再跑 `--architecture=gfx906`；出 `.s` 后 `amdclang++ -x assembler` 才算 P0 PASS。

## 3 R17 支线（已编译，未部署）

补丁（`src/prefill/prefill.cpp`，+11 行）在 `mmq_plan()` 末尾无条件打印：

```
strata: prompt experts: MMQ <n> / fused <n> / FP16 <n> of <n> layers (no fallback | some layer falls back)
```

**为什么值得占一次构建**：生产日志现在看不出三路分布，而相位表里的 `dequant`
在 MMQ 路径下其实是 **gather**（W795 自己写过"dequant（实为 group gather）"）。
R14 的"反量化能不能摊薄"这个前提，取决于三路各几层——先看分布再谈优化。

| 项 | 值 |
|---|---|
| 分支 | `gfx906/mmq-plan-banner @ ec368906`（从 `aef9d256` 开出） |
| 构建 | `gfx-mmq-build/strata`，**configure rc=0 / ninja rc=0**，38,567,776 B，md5 `a10af3849a65724c81d215e3834f1b91` |
| 与生产的差 | 生产 `29b15bb4…`（38,567,520 B）；本分支只多这一行打印 |
| 部署 | **未部署**，等 R15 的停服窗口一起做 |

## 4 台账同步（本轮改了什么）

| 文件 | 改动 |
|---|---|
| `AUDIT16_W844_W853.md` | P0-4 标**撤回**（正文 + 总判 + 整改行）；新增 **§11 误判复盘**；复核命令改成 `grep -c STRATA_PREFILL_MMQ=1 build.ninja` |
| `W832_OPT_PLAN_V2.md` | §6.2 R16 行改写成"已撤回 + 为什么"；§6.5 队列：**R15 升第 1 序、新增 R17 第 2 序**，R16 移出 |
| `PROGRESS.tsv` | `R16` → `DONE_NEG`（撤回，记理由）；新增 **`R17`** OPEN |
| `params/PARAM_REGISTER.tsv` | `P232` → `CORRECTED`：选项 ≠ 定义，附编译行证据与误判链 |
| `AUDIT_INDEX.md` | AUDIT16 行标"P0-4 已撤回"；未结清表：删"MMQ 构建门"、加"MMQ 层分布 / dequant 语义" |

## 5 下一枪（按 §6.5 新序）

**一次停服里做两件事**（§6.5 权重④"战线集中"）：

1. **R15**：`--pcie-frac 0.20 → 0.30/0.35` 两臂，`STRATA_PREFILL_TIMING=1`，只看 `wait copy` 与 `read` 是否同向；
2. **R17**：把 `gfx906/mmq-plan-banner` 的二进制换上去，读那行 banner（三路层数），
   顺便复核 `dequant` 相位在 MMQ 路径下的数值是否就是 gather。

判据：R15 看 read ≥5%（否则记"不可判"）；R17 只看归因，不看收益。
回滚：`/data/bin/strata-0.1.55g`（`29b15bb4…`）+ 配置 `STRATA_PREFILL_TIMING` 删掉 + `--pcie-frac 0.20`。

## 6 生产（本轮未动）

| 项 | 值 |
|---|---|
| 容器 / 镜像 | `strata166-407` / `strata-gfx906:0.2.9-101`，started `2026-10-31T15:42:42Z`，restarts=0 |
| 引擎 | `/data/bin/strata-0.1.55g`（`29b15bb4…`） |
| userland / 表 | ROCm 10.1.0 / rocBLAS 5.7 / 84 行表 |
| 分支 | 主线 `gfx906/0.2.9-mi50 @ aef9d256`；两条支线 `d9d6ab8b`（hipBLASLt）、`ec368906`（R17 banner） |
