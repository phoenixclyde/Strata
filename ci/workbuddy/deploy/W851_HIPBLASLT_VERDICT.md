# W851 · hipBLASLt 表能不能做出来？（结论：不能，且不需要）

> **AUDIT16 补记**：① 本节引用的探针输出当时**没有落盘**（只留了 `.cpp`），AUDIT16 已用
> `strata-gfx906:0.2.9-101` 重跑并留证：`166:~/strata166/data/w856_probe_hblt_101.txt`，输出与下面**逐字一致**。
> ② §1.3 引的 `ROCm/hipBLASLt#1243` 与 `pytorch#138067` 正文**都不含 gfx906**（已 closed，2024-10），
> 只能当"库在不支持架构上会硬报错"的旁证，不是 gfx906 的直接证据。

> 2026-10-31 21:4x。机主问「hipBLASLt 表是什么，有可能做出来吗」。本件是三层证据 + 一条替代路线。
> 一句话：**hipBLASLt 在 gfx906 上一个可用解都没有，因为 AMD 从未为这代卡编译过它的内核；
> 「做一张表」的前提（库里有若干个可枚举的 solution）不存在。** 而 rocBLAS 那条路是通的，且已吃到 2.4×。

## 1 两套表是什么关系

引擎 `src/prefill/gemm.cu` 里并行存在两条 GEMM 后端，各自带一张「按形状选内核」的调优表：

| | hipBLASLt | rocBLAS |
|---|---|---|
| 头文件 | `hipblaslt_tuning.hpp` | `rocblas_tuning.hpp` |
| 表头魔数 | `STRATA_HIPBLASLT_TUNING_V1 <arch> <version>` | `STRATA_ROCBLAS_TUNING_V1 <arch> <version>` |
| version 语义 | hipBLASLt 主次版本整数（如 `100401`） | rocBLAS **完整版本串**（`5.5.0.cd957402309`） |
| 行的内容 | `type N K ldy T solution`，**solution 就是 algo 编号** | 同左（`f16o ... solution`） |
| 上游给了哪些表 | `tools/hip/gfx1100|1103|1150|1151|1200|1201-hipblaslt-*.txt`，**全是 RDNA3/RDNA4** | `tools/hip/gfx1030-rocblas-5.6.0.8d1ae90e.txt` 一张样例 |
| 我们的表 | **没有**（也不可能有，见 §2） | `/data/gfx906-rocblas-5.5.0.txt`，56 行 / 47 有解 |

**表的本质**：GEMM 库自带一堆预编译内核（solution），库自己按形状猜一个，猜得常常不是最快的。
工具（`tools/hip/tune_rocblas.cpp`）把这些 solution **逐个枚举 + 计时 + 校验输出**，把「比默认快 ≥5%」的
那一个的索引写进表；引擎运行时用 `rocblas_gemm_algo_solution_index` 直接点名那个内核。

⇒ 所以「做表」的**必要前提是库里已经有一批能枚举的 solution**。这一点在 gfx906 的 hipBLASLt 上不成立。

## 2 三层证据：gfx906 的 hipBLASLt 没有任何 solution

### 2.1 实测（最硬）：两代 ROCm 都一个 algo 也拿不到

自己写的探测程序（`albus/w851/probe_hblt.cpp`，用与引擎 `f16_inplace` 同形的参数：
FP16 in/out、FP32 累加、`C[N×T] = Wᵀ·X`，形状取引擎 14 个之一 `T=256 N=10240 K=2560`），
在 **7.14** 与 **10.1** 两个镜像上都跑：

```
rocblaslt error: Could not load "TensileLibrary_lazy_gfx906.dat"
hipModuleLoad failed: Kernels.so-000-gfx906.hsaco            error: file not found
hipModuleLoad failed: Kernels.so-000-gfx906-xnack-.hsaco     error: file not found
hipModuleLoad failed: Kernels.so-000-gfx906-xnack+.hsaco     error: file not found

hipblasLtMatmulAlgoGetHeuristic -> status=3  algos=0      (3 = HIPBLAS_STATUS_NOT_SUPPORTED)
小形状 256x256x256              -> status=3  algos=0
```

**关键细节**：hipBLASLt **认识 gfx906 这个名字**（它去点名要 `TensileLibrary_lazy_gfx906.dat`），
但那个文件 AMD 从来没发布过。对比同镜像里的 rocBLAS：

```
/opt/rocm/lib/rocblas/library/Kernels.so-000-gfx906.hsaco            228K   ← 齐全
/opt/rocm/lib/rocblas/library/TensileLibrary_Type_..._gfx906.dat      42K
```

⇒ **gfx906 的 GEMM 内核只在 rocBLAS 里，hipBLASLt 里没有。**

### 2.2 上游源码：gfx906 连「支持架构白名单」都不在

`ROCm/rocm-libraries` → `projects/hipblaslt/cmake/tensilelite_supported_architectures.cmake`（develop 分支）：

```cmake
set(SUPPORTED_ARCHITECTURES
    "gfx908" "gfx90a" "gfx942" "gfx950"
    "gfx1100" "gfx1101" "gfx1102" "gfx1103"
    "gfx1150" "gfx1151" "gfx1152" "gfx1153"
    "gfx1170" "gfx1171" "gfx1200" "gfx1201" "gfx1250" ...)
```

**没有 gfx906**（也没有 gfx900/gfx803）。而 `CMakeLists.txt:146` 有一句 `tensilelite_validate_gpu_targets("${GPU_TARGETS}")`
—— 传 `gfx906` 会直接被拒。文件里还专门写了注释解释为什么 gfx10XX 不进默认 all 构建（extops 不支持旧设备），
即：**连 gfx1030 都只是「技术上能编、默认不编」，gfx906 是「连名单都不在」。**

### 2.3 我们自己的构建：hipBLASLt 路径根本没编进去

`CMakeLists.txt:848`：

```cmake
if(STRATA_ENABLE_HIP AND STRATA_HIPBLASLT_AVAILABLE)      # ← 需要 STRATA_ENABLE_HIP
    target_compile_definitions(strata_prefill PRIVATE STRATA_HIPBLASLT_AVAILABLE=1)
```

而我们是 `STRATA_HIP_GFX906=ON`，且 `CMakeLists.txt:89` 明确
`if(STRATA_HIP_GFX906 AND STRATA_ENABLE_HIP) FATAL_ERROR`（两者互斥）。
⇒ 我们的二进制里 `gemm.cu` 那 400 多行 hipBLASLt 代码是**编译期就被剪掉的**。
（rocBLAS 那条门控是我们补过的：`if((STRATA_ENABLE_HIP OR STRATA_HIP_GFX906) AND STRATA_ROCBLAS_AVAILABLE)`。）

## 3 「做出来」需要什么，以及为什么不值得

要把 gfx906 的 hipBLASLt 表做出来，得先做**库本身**：

1. 改上游白名单 + 绕过 `validate_gpu_targets`；
2. 用 TensileLite 为 gfx906 写/调 logic（`Tensile/Logic/asm_full/gfx906/*.yaml`）——
   gfx906 是 wave64 + 无 MFMA（矩阵核只有 V_DOT2/DPP），TensileLite 的 asm 生成器里虽然有 gfx906 的枚举
   （`rocisa/include/helper.hpp` 命中 gfx906），但**没有任何 gfx906 的 tuning logic**；
3. 用 `hipblaslt_create_device_library`（`HipBLASLtCodegen.cmake`）生成 `TensileLibrary_lazy_gfx906.dat`；
4. 自己验证数值正确性（输出对拍）+ 逐形状调优；
5. 再回到 Strata 里把 `STRATA_ENABLE_HIP` 与 `STRATA_HIP_GFX906` 的互斥拆开，重编引擎。

这是**给 AMD 补一个后端**（以周计，且没有上游保证），不是「做一张表」。
而它要替换的 rocBLAS 路径**已经在吃同样的收益**（见 §4），还多一份社区验证。

## 4 替代路线：rocBLAS 表，而且我们还没吃满

### 4.1 rocBLAS 这条路的收益是实测过的（同卡 gfx906）

社区项目 `xxDoman/strata-gfx906` 的 `llms.txt`（2026-10-21）给的是**同代卡、但不是同引擎**的数（**regime：2 卡分片 MI50+Radeon VII / IQ3_XXS / engine 0.1.43.1 / ROCm 7.2.1 / ctx 131072**；AUDIT16 P1-9）：

> The gfx906 rocBLAS solution table: **4K 460.7 vs 384.9 (+19.7%)**、**16K 544.9 vs 438.6 (+24.2%)**，
> first token 16–20% earlier, decode unmoved.

我们自己这张表的单形状实测（W851，rocBLAS 5.7）：`N=10240 K=2560`、T=256 **1.898 → 0.774 ms（2.45×）**。

### 4.2 但我们的表只覆盖 T ≥ 1024

现有 `/data/gfx906-rocblas-5.5.0.txt` 的 token 桶只有 **1024 / 2048 / 4096 / 8192**。
而 `rocblas_tuning.hpp::closest()` 的语义是「取最近的桶（并列取小）」⇒
**T=256 和 T=512 的请求会用 T=1024 那一行的 solution**，而那一行是为 1024 选的内核。

刚测出来的事实是：同一个形状在 T=256 上，**专为 256 选的内核**比库自己的默认快 2.45×，
而在 T=512 上快 1.90×。这正是 W804 记的「1–3K 是 staging+CPU」那一段——
**小 chunk 是 prefill 最贵的地方，而表在那里是空白**。

⇒ 结论：**真正的增量不是「换 ROCm 10.1」，而是「给现有表补 256/512 两个桶」**。
5.5 与 5.7 的内核性能逐形状对比几乎一致（`N=10240 K=2560`：T=1024 是 2.788 vs 2.793 ms，差 0.2%），
所以这次收益**不需要换 ROCm 就能拿到**。

## 5 判词

| 问题 | 答案 | 依据 |
|---|---|---|
| hipBLASLt 表是什么 | 让 hipBLASLt 跳过它自己的启发式、点名某个预编译内核的索引表 | §1 |
| gfx906 上能做吗 | **不能** | §2.1 实测 algos=0 + §2.2 白名单无 gfx906 + §2.3 构建不编 |
| 要硬做需要什么 | 给 hipBLASLt 补 gfx906 的 TensileLite logic + codegen + 数值验证 + 拆互斥宏 | §3 |
| 值不值得 | **不值得**：rocBLAS 路径已吃 2.4×/形状，社区同卡 +19.7%(4K)/+24.2%(16K) | §4.1 |
| 该做什么 | **补 256/512 桶**（现有表从 1024 起），5.5 就能拿，不用换 ROCm | §4.2 |

## 6 附：这次顺带更正的一条旧说法

上一轮（W848）我写「`/opt/rocm/lib/hipblaslt/library` 里 gfx906 命中 0」——
那个目录**根本不存在**（两代镜像都没有），所以「命中 0」是空目录的产物，证据链是断的。
结论碰巧对，但**判据要换成**：`TensileLibrary_lazy_gfx906.dat` 不存在 + `AlgoGetHeuristic` 返回 0。
