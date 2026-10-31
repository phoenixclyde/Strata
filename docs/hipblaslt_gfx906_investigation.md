# hipBLASLt on gfx906 (MI50/MI60): 完整调查记录

> 调查周期：2026-10 下旬 ~ 2026-11-01
> 环境：ROCm 10.1（clang 24.0），gfx906:sramecc+:xnack-，Ubuntu 22.04
> 结论：**hipBLASLt 在 gfx906 上不可用**，且不是配置问题 —— 新版 TensileLite 把 non-MI 的
> 守卫条件拆了。可用路径是 rocBLAS（本机生产即如此）。

---

## 0 TL;DR

| 问题 | 答案 |
|---|---|
| gfx906 能生成 hipBLASLt kernel 吗 | **能**。190 968 B `elf64-amdgpu`，63 条 `v_fma_mix_f32` |
| 能打包成运行时认的库吗 | **能**。msgpack + YAML 双路径，`libhipblaslt.so` 自建成功 |
| 能跑起来吗 | **不能**。`AlgoGetHeuristic` 永远 0 个解 |
| 卡在哪 | **TensileLite 的 non-MI codegen 路径**：`KernelWriterAssembly` 无条件读 17 个 `MI*` 键，而 `Solution` 只在 MI 分支设 |
| 谁的责任 | 上游。gfx906 早在 hipBLASLt 支持列表外（TheRock 文档明说） |
| 有可用的替代吗 | **有，而且已经在跑**：rocBLAS 的 gfx906 调优表（137 个解） |

**给后来者的一句话**：gfx906 上不要碰 hipBLASLt。GEMM 走 rocBLAS，GEMV 自己写 kernel。

---

## 1 背景

目标是在 MI50（gfx906，无 MFMA/WMMA）上让 vLLM 的 GEMM 走 hipBLASLt，期望比 rocBLAS 更快。

前提事实：
- gfx906 **无矩阵指令**（既无 MFMA 也无 WMMA）⇒ Tensile 走 `EnableMatrixInstruction=False` 的 non-MI 路径
- rocBLAS **支持** gfx906（`/opt/rocm/lib/rocblas/library/gfx906/`，AMD 预编译，137 个解）
- hipBLASLt **不支持**（无 `lib/hipblaslt/library/gfx906`）

---

## 2 二十轮推进

每一轮都是「跑 → 报错 → 读源码定位 → 修 → 再跑」。记下来是为了让后来者不必重复。

### 阶段一：能不能生成 kernel（W851 ~ W858，前 7 层）

| 层 | 做了什么 | 结果 |
|---|---|---|
| 1 | 自建 rocisa（`rocisa-install`） | ✅ |
| 2 | 自编 hipBLASLt 主机库 | ✅ 61/61 |
| 3 | 让 gfx906 进白名单 | ✅ `tensilelite_supported_architectures.cmake:27` 追加 |
| 4 | 库加载 | ✅ `status=0` |
| 5 | codegen | ✅ 190 968 B ELF |
| 6 | 指令校验 | ✅ 63 条 `v_fma_mix_f32` |
| 7 | 包成 hipBLASLt 库 | ⚠️ 格式对不上 |

**关键**：这七层证明「**能力存在**」。后面所有问题都不是 gfx906 不行。

### 阶段二：把 rocBLAS 的 logic 迁到 hipBLASLt 的 schema（W861，13 轮）

来源：`/opt/rocm/lib/rocblas/library/` 反解出的 `vega20_Cijk_Ailk_Bjlk_HHS_BH.yaml`
（gfx906 + f16 + HPA，128 个解，AMD 自家调优结果）。

| 轮 | 报错 | 根因 | 修法 |
|---|---|---|---|
| 1 | `parse_scalar` AssertionError | 以为是 flow style | 摊成 block → **报错不变**，假设错 |
| 2 | 同上 | 以为是 `null` 值 | 26 处 `null` 全在 value 位，不是它 |
| 3 | 同上 | **YAML 锚点**：`ThreadTile: &id001` 共 21 处；`CustomYamlLoader.parse_general` 只认 Mapping/Sequence/Scalar，遇 `AliasEvent` 返回 None **且不消费事件** ⇒ 状态机永久错位 | `Dumper.ignore_aliases -> True` 展开 → **loader 全通** |
| 4 | `missing required field matching property` | `parseLibraryLogicList` 要 12 元素，旧文件 9 个 | 补 `[9]TileSelection=None [10]PerfMetric=None [11]LibraryType` |
| 5 | `KeyError: EnableMatrixInstruction` | `Solution.py:846` 推断完**没写回 state**，928 行直接读 | 转换侧补 `False` |
| 6 | `No valid DepthU found` | 缺 MX/subtile/metadata 一族字段，默认值让 GLVW 校验全线失败 | **`NoReject: True`** —— `Utilities.py::reject()` 第一行就认这个键 |
| 7 | `KeyError: ActivationComputeDataType` | 该键属 **ProblemType**，而 `ProblemType(...)` 构造时**没有** defaultSolution 兜底（Solution 有） | 让 `ProblemType(minimal, False).state` 自己吐 90 键当模板 |
| 8 | `Unknown assertion key: AssertMinApproxSize` | `Contractions.py::ProblemPredicate.FromOriginalKeyPair` 只认 3 类 Assert* | 剔掉废弃键 |
| 9 | `KeyError: ExpertSchedulingMode` | DefaultSolution 补齐仍不够 | 换「以别的架构为骨架」 |
| 10 | `'int' object is not subscriptable` | `IsaVersion(isa[0],…)` 要三元组，给了 `ISA=906` | 删掉 ISA，交给 `gfxToIsa(arch)` |
| 11 | **类型不匹配 545 处** | `DirectToLds`/`PrefetchGlobalRead`/`PrefetchLocalRead`/`UseSgprForGRO`/`VectorStore` 是 bool 但要 int；`Use64bShadowLimit` 反之。msgpack 里 wire type 不同 ⇒ `std::bad_cast` | 按 `validParameters` 声明自动归一 |
| 12 | `KeyError: NumLdsBlk` | `Solution.py:5522` 在 **MI 分支**赋值，`KernelWriter._initKernel:7437` **无条件**读 | 补默认值 2 |
| 13 | `KeyError: NumTotalPackedLoadsA` | 同一族的又一个 | —— **判定此路不通** |

**第 13 轮的判断**：不是「再补一个」，是一整族 `Num*` / `MI*` 字段只活在 MI 路径。

### 阶段三：走官方产线（本轮，最后 8 轮）

`--build-only` 会打印 `# Build-only mode: skipping LibraryLogic`，所以真 benchmark 必须编
`tensilelite-client`。这一阶段有四个实打实的发现。

---

## 3 四个真突破（含源码依据）

### 突破 1：`hipblasLtCreate` 一进来就 `exit(1)` —— 是我们自己的 LLVM 抢了符号

用 `LD_PRELOAD` 钩掉 `exit()` 抓 backtrace：

```
libhipblaslt.so.1(hipblasLtCreate+0x6e)
libamdhip64.so.7(hipMemset+0x25)
libamd_comgr.so.3(amd_comgr_do_action)
libclang-cpp.so.24.0git(clang::ExecuteCompilerInvocation)
libhipblaslt.so.1(llvm::cl::ParseCommandLineOptions …)   ← 关键
exit(1)
```

`llvm::cl::ParseCommandLineOptions` **落在我们自己的 `.so` 里**。原因在
`tensilelite/CMakeLists.txt`：

```cmake
if(HIPBLASLT_ENABLE_YAML)
    target_link_libraries(tensilelite-host PRIVATE LLVMObjectYAML)   # 静态链进 LLVM
```

comgr 想用它自己那份 clang，却撞上我们的 LLVM 符号（ELF 符号插桩），参数版本对不上就 `exit(1)`。

**修法**：`-DHIPBLASLT_ENABLE_YAML=OFF`（走纯 msgpack）。

**效果**：`.so` 里 `ParseCommandLineOptions` 归零，体积 11.7 MB → **8.40 MB**，
`hipblasLtCreate` 立刻 `status=0`、`LIBPATH=<我们给的路径>`。

> 教训：报错信息说 `--amdhsa-code-object-version=5` 未知参数，很容易被判成「comgr 坏了 / AMD 放弃旧架构」。
> 实际是被我们自己的库插桩了。

### 突破 2：`LoadLibraryMapping` 是 undefined symbol

`nm -D` 里 `MessagePack` 符号 0 个、`LoadLibraryMapping` 是 `U`。源码：

```cmake
if(HIPBLASLT_ENABLE_YAML)
    ... TENSILE_YAML        # 只定义 YAML
else()
    ... TENSILE_MSGPACK     # 才定义 MSGPACK
endif()
```

而 `TensileLite::LoadLibraryMapping` 的定义在 `#ifdef TENSILE_MSGPACK` 里 ⇒ **开 YAML 编出来的库必然缺符号**。

**修法**：YAML 分支里额外补 `src/msgpack/MessagePack.cpp` + `-DTENSILE_MSGPACK`。

### 突破 3：`mxDataGenerator` 是误判

一度判定「缺兄弟仓库源码，无法编 client」。实际拆下来只有一个真缺件：

| 报错 | 真因 | 修法 |
|---|---|---|
| `mxDataGen.hpp file not found` | 头**就在树里** `clients/common/include/mxDataGen.hpp`，只是 client 编译命令**没加这个 include** | `-I .../clients/common/include` |
| `mxDataGenerator/*.hpp`（6 个 ocp_*） | 只被 `DataInitializationHelpers.hpp` 引用，该 TU 没编到 | 无需处理 |
| `undefined symbol: mxScaleLayoutForArchName` | 实现在 `clients/common/src/mxDataGen.cpp`（那个文件才依赖 DGen），但**函数本身 8 行、零外部依赖** | 写 `mx_stub.cpp` 只实现它；gfx906 落到 `MXScaleLayout::None` |

**结果**：`tensilelite-client` 编成，12 016 552 B。

### 突破 4：一个纯大小写的坑

```
add_subdirectory(.../shared/mxdatagenerator) which is not an existing directory
```

选项名是 **`HIPBLASLT_ENABLE_MXDATAGENERATOR`（全大写）**，一直传小写 `hipblaslt_...`，
CMake 变量**大小写敏感** ⇒ OFF 从未生效。改正后 cfg rc=0、0 error。

而 `clients/common/CMakeLists.txt` 头注释写明：只有该开关 ON 且存在 consumer 时才被 `add_subdirectory`。

---

## 4 终局：三条外部证据

### 4.1 官方文档（TheRock gfx906 构建笔记）

> **hipBLASLt does not support gfx906**: upstream excludes it from
> `tensilelite_supported_architectures.cmake`, there is no vega20 logic...
> The install has `lib/rocblas/library/gfx906` but **no `lib/hipblaslt/library/gfx906`**.
> **Anything that calls hipBLASLt directly fails at heuristic selection.**

### 4.2 本树源码实况

`cmake/tensilelite_supported_architectures.cmake`：

```cmake
set(SUPPORTED_ARCHITECTURES
    "gfx908" "gfx90a" "gfx942" "gfx950" "gfx1100" … "gfx1250"
  gfx906            # ← 缩进只有 2 空格，人工追加，非上游原样
)
```

gfx906 被人工加进去了，所以构建能一路跑到底；但 `BASE_ARCHITECTURES` 仍是空集，
`-DGPU_TARGETS=all` 不会带上它。

### 4.3 旧版 Tensile 对照（`ROCm/Tensile@develop_deprecated`）

拉到旧版 `Tensile/SolutionStructs.py`（233 293 B，支持 gfx906 的那版）对比：

```python
# 旧版 1920 行 —— 和现代版一样，MI 字段只在 MI 条件下填
if  ("MIBlock" in state and len(state["MIBlock"]) == 6) \
    and ("MIWaveTile" in state and len(state["MIWaveTile"]) == 2):
```

**Solution 侧两边一致**。差别在 KernelWriter：

| | 旧版（支持 gfx906） | 现代 TensileLite |
|---|---|---|
| `Solution` 侧 | MI 字段只在 MI 分支设 | 同上 |
| `KernelWriterAssembly` | non-MI 路径**不读**这些字段 | **无条件读** 17 个 `MI*` 键 |
| 结果 | non-MI 正常出 kernel | KeyError / 补默认值后**地址算错** |

`KernelWriterAssembly.py` 里被无条件读的键：

```
MIArchVgpr, MIBlock, MIInputPerThread, MIInputPerThreadA, MIInputPerThreadB,
MIInputPerThreadMetadata, MIInputPerThreadMXSA, MIInputPerThreadMXSB,
MIOutputVectorWidth, MIRegPerOut, MIWaveGroup, MIWaveTile, MIWaveTileA, …
```

**这就是根因**：现代版重构时把 non-MI 的守卫条件拆掉了。

---

## 5 为什么"补字段"不可行（机理）

那 17 个 `MI*` 字段在 `KernelWriterAssembly` 里**参与地址/偏移计算**：

```python
# :1275
ri += ceil(kernel["VectorWidthA"] * tPA["bpe"] / bpr) * kernel["MIWaveTileA"] // kernel["VectorWidthA"]
```

non-MI 的 LDS 布局与 MI 完全不同。拿 gfx908 的值填进去：

- **不会报错**
- **kernel 能跑**
- **结果错一个数**

这是最危险的一类失败。补默认值 = 制造静默错误。

**真正修好需要**：`KernelWriterAssembly` 里几十处读取点加回 `if EnableMatrixInstruction:` 守卫
—— 一次上游级重构。且即便改完，旧版 Tensile 产出的库是 rocBLAS 格式
（`TensileLibrary_Type_*_gfx906.dat`），hipBLASLt 不认，还要再做一层 schema 转换。

---

## 6 可复现清单

### 关键构建参数

```bash
cmake -S hipblaslt -B build -G Ninja \
  -DCMAKE_BUILD_TYPE=Release \
  -DCMAKE_C_COMPILER=/opt/rocm/llvm/bin/clang \
  -DCMAKE_CXX_COMPILER=/opt/rocm/llvm/bin/clang++ \
  -DCMAKE_HIP_COMPILER=/opt/rocm/llvm/bin/clang++ \
  -DCMAKE_HIP_ARCHITECTURES=gfx906 -DGPU_TARGETS=gfx906 \
  -DCMAKE_CXX_FLAGS="-I<msgpack-include> -I<hipblaslt>/clients/common/include \
                     -DMSGPACK_ENDIAN_LITTLE_BYTE=1 -DMSGPACK_NO_BOOST=1" \
  -DTensile_SKIP_BUILD=ON -DTENSILELITE_ENABLE_HOST=ON \
  -DTENSILELITE_ENABLE_CLIENT=ON -DTENSILELITE_BUILD_SHARED_LIBS=OFF \
  -DHIPBLASLT_ENABLE_CLIENT=OFF \
  -DHIPBLASLT_ENABLE_YAML=OFF \          # ← 关键：关掉，否则 LLVM 抢 comgr 符号
  -DHIPBLASLT_ENABLE_EXTOPS=OFF -DHIPBLASLT_ENABLE_ROCROLLER=OFF \
  -DHIPBLASLT_ENABLE_MXDATAGENERATOR=OFF \  # ← 全大写，小写不生效
  -DHIPBLASLT_ENABLE_LAZY_LOAD=ON
```

### 必需的源码补丁

| 文件 | 补丁 | 原因 |
|---|---|---|
| `tensilelite/CMakeLists.txt` | YAML 分支补 `MessagePack.cpp` + `-DTENSILE_MSGPACK` | 否则 `LoadLibraryMapping` 是 U |
| `tensilelite/client/src/mx_stub.cpp` | 新增，实现 `mxScaleLayoutForArchName` | 8 行，零依赖 |
| `tensilelite/client/CMakeLists.txt` | `target_sources(... PRIVATE src/mx_stub.cpp)` | **不能**在 `add_library()` 后直接跟源文件名 |
| `library/src/amd_detail/hipblaslt.cpp` | 两处 `hipMemset` 改非致命（可选） | 仅当 comgr JIT 仍失败时 |

### 库文件命名（易错点）

`MasterSolutionLibrary.hpp:132` **硬要求**文件名以 `TensileLibrary_lazy_` 开头：

```cpp
const std::string prefix = "TensileLibrary_lazy_";
if(stem.compare(0, prefix.size(), prefix) != 0) {
    "Cannot derive arch from " << tensileLibPath;  return false;
}
```

所以 `LAZY_LOAD=OFF` 配 `TensileLibrary_gfx906.dat` **必定失败**——这个前缀检查不看开关。

### 产物

| 文件 | 大小 | 说明 |
|---|---|---|
| `Kernels.so-000-gfx906.hsaco` | 190 976 B | 真 kernel，含 `v_fma_mix_f32` |
| `libhipblaslt.so.1.4`（含 client） | 12.0 MB | 自编 |
| `tensilelite-client` | 12 016 552 B | benchmark 执行器 |

---

## 7 建议

1. **不要试图在 gfx906 上用 hipBLASLt**。三条独立证据（官方文档 / 源码实况 / 旧版对照）+ 二十轮实测。
2. **GEMM 走 rocBLAS**。`/opt/rocm/lib/rocblas/library/gfx906/` 有 AMD 的 137 个调优解，
   这是 gfx906 上的最优解，hipBLASLt 即便通了天花板也是它。
3. **GEMV 不在 rocBLAS 覆盖范围内**（GEMV 不走 GEMM 路径），那里才是自主优化的空间。
4. 如果未来上游把 non-MI 守卫补回来，本文 §6 的构建参数可直接复用。

---

## 附：关键源码索引

| 位置 | 内容 |
|---|---|
| `tensilelite/CMakeLists.txt` | YAML/msgpack 二选一（缺符号的源头） |
| `tensilelite/include/Tensile/MasterSolutionLibrary.hpp:132` | `TensileLibrary_lazy_` 前缀硬检查 |
| `tensilelite/include/Tensile/PlaceholderLibrary.hpp:165` | lazy 子库加载路径拼法 |
| `tensilelite/Tensile/SolutionStructs/Solution.py:846,928` | `EnableMatrixInstruction` 推断未写回 |
| `tensilelite/Tensile/SolutionStructs/Solution.py:2219-2232` | `MIWaveTileA/B` 只在 MI 分支设 |
| `tensilelite/Tensile/SolutionStructs/Utilities.py::reject` | `NoReject` 口子 |
| `tensilelite/Tensile/KernelWriter.py:7437` | `NumLdsBlk` 无条件读 |
| `tensilelite/Tensile/KernelWriterAssembly.py:1140,1275,1375` | `MI*` 字段参与地址计算 |
| `library/src/amd_detail/rocblaslt/src/tensile_host.cpp:2805,2945` | `lazyLoad = ROCBLASLT_TENSILE_LAZY_LOAD`（编译期） |
| `clients/common/CMakeLists.txt:1-60` | `HIPBLASLT_ENABLE_MXDATAGENERATOR` 开关与 consumer 条件 |
