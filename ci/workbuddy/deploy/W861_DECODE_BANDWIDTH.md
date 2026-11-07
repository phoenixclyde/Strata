# W861 · 靶心重排 —— decode 占 55.4%，短档只占 1.2% 的 read 时间

> ⚠️ **本件第 3 节的绝对数字已被 W862 推翻，不要再引用（2026-11-01 14:3x 加，见 `AUDIT17` P0-1/P0-2）**
>
> - 本件 §3 的逐矩阵表（shared gate/up **22%**、每层 **279.5 µs**）**复现不出来**：它用的是
>   `copies = min(16, 512MB/bytes)` ⇒ ~2.3 GB footprint，而显存现在只剩 ~870 MB，那个配置跑不起来。
>   同口径重测是 **210.9 µs/层、45–71%**（W862 §1）。
> - 由它推出的 **「dense GEMV 占 23 ms 的 59%」与「约 9.1% 的总时间」都要重算**：
>   ① 每层不是 9 个矩阵（36 GDN + 12 QSA，`full_attention_interval=4`）；
>   ② 日志明示 `STRATA_HC_Q8=1: 0.63 GiB` 的 HC Q8_0，而本件假设只有 334 MB；
>   ③ 除数在 W861（接受 token 数 2.36）与 W862（列数 6）之间不一致，差 2.54 倍。
> - 仍然成立的部分：§1 的**时间加权**（read 44.6% / gen 55.4%）、§2 的按 prompt 桶二维拆分、
>   §4 的 hipBLASLt 记录（但 190 968 / 190 976 / 219 448 三个字节数需按 AUDIT17 P0-3 对账）。

> 生成：2026-11-01 04:2x–05:0x（UTC 20:2x–21:0x）
> 触发：机主"继续多线并行推进"+"llama.cpp 不是 166 上现成的吗"+"能转格式吗"
> 一句话：**这一轮把"哪里慢"从合成探针换成了真实流量的时间加权，结论与此前排序相反**；
> 并把 decode 的 23 ms/token 拆到了 kernel 级。

---

## 1 时间加权账（这是本轮最重要的数字）

数据源：`/data/strata-huihui-ud-iq4_xs.log`，5359 条真实请求（跨 24 天、665 次引擎启动）。
脚本：`albus/w861/time_weight.py`、`albus/w861/decode_split.py`（只读日志，零干扰）。

```
总时间 107 678.8 s = read 48 001.0 s (44.6%) + gen 59 677.8 s (55.4%)
```

| prompt 桶 | 条数 | 条数% | read s | read% | gen s | gen% | **占总时间** | ms/1k_new | read tok/s |
|---|---|---|---|---|---|---|---|---|---|
| 0–128 | 766 | 14.3% | 583.8 | **1.2%** | 2 997.8 | 5.0% | **3.3%** | 19 441 | 51 |
| 128–256 | 51 | 1.0% | 107.6 | 0.2% | 5.3 | 0.0% | 0.1% | 9 593 | 104 |
| 256–512 | 247 | 4.6% | 503.1 | 1.0% | 84.5 | 0.1% | 0.5% | 5 304 | 189 |
| 512–1K | 662 | 12.4% | 1 701.5 | 3.5% | 124.6 | 0.2% | 1.7% | 4 189 | 239 |
| 1K–4K | 546 | 10.2% | 2 244.9 | 4.7% | 884.5 | 1.5% | 2.9% | 2 498 | 400 |
| 4K–16K | 723 | 13.5% | 4 643.1 | 9.7% | 1 950.3 | 3.3% | 6.1% | 2 040 | 490 |
| 16K–64K | 766 | 14.3% | 18 547.5 | **38.6%** | 10 707.7 | 17.9% | 27.2% | 2 004 | 499 |
| **64K+** | 1 598 | 29.8% | 19 669.6 | **41.0%** | 42 923.0 | **71.9%** | **58.2%** | 2 432 | 411 |

短档合计：`prompt<128` → 766 条（14.3%）但只占 **1.2% 的 read 时间 / 3.3% 的总时间**。

### 1.1 这条推翻了什么

`R19`（短档固定开销）此前排第 2，理由是"0–128 档每 token 贵 9.5×"（19 441 vs 2 039 ms/1k）。
**这个倍数是对的，但它乘上 token 数就微乎其微**：那 766 条一共只有 30 030 个 read token，
而 64K+ 档 1 598 条有 8 087 886 个 —— 相差 269 倍。

⇒ **即使把短档 read 时间压到 0，总时间也只降 1.2%。R19 降级为"低价值、不单独占停服"。**

---

## 2 decode 是平的：23 ms/token，不随上下文长度变化

按 prompt 桶 × gen 长度桶的二维分解（`decode_split.py`），单位 ms/token：

| prompt \ gen | 1–64 | 64–256 | 256–1 024 | 1 024+ |
|---|---|---|---|---|
| 0–1 024 | 24.3 | 23.3 | 22.5 | 24.0 |
| 1K–8K | 25.1 | 19.0 | 19.8 | 23.9 |
| 8K–16K | 23.7 | 19.5 | 22.5 | 22.2 |
| 16K–64K | 23.9 | 22.7 | 20.2 | 23.2 |
| **64K+** | **23.6** | **23.8** | **24.0** | **23.7** |

**65 倍上下文差异，decode 成本差不到 5%。** 两个后果：

1. **"长上下文掉速"不成立**。64K+ 档占 58.2% 总时间，纯粹因为**用户在那里生成了 1 807 418 个 token**
   （占全部生成 token 的 71.3%），不是因为慢。
2. **int8 KV（`M3`）对 decode 无收益**。若 KV 读取主导，65K 上下文必然比 1K 慢一个量级。
   实测平 ⇒ 瓶颈不在 KV。`M3` 只应作为"prefill 代价"评估，不再当作 decode 手段。

引擎自报的 `adaptive tier ... N ms per token`（159 条）落在 **21.06–25.95 ms**，与本表独立吻合。

---

## 3 decode 的 23 ms 拆到 kernel 级：dense GEMV 占 59%

工具：`b6_mmvq_bench`（decode 的 dense 投影，**模型自己的形状与格式**，每个 launch 用 CUDA events
包起来、500 次取中位、权重轮转多份超 L2 以模拟冷读；**GPU time only，免疫主机与生成文本**）
+ `q8_gemv_bench`（同一批 kernel 对 711 GB/s 的达成率）+ `router_chain_bench`（router 链）。

### 3.1 单 token 的 dense 调用（ncols=1，ms）

| kernel | 格式 | 单次 ms | ×48 层 |
|---|---|---|---|
| gdn qkv | IQ4_XS | 0.0466 | 2.24 |
| gdn qkv | Q6_K | 0.0530 | 2.54 |
| gdn gate | Q6_K | 0.0365 | 1.75 |
| gdn out | IQ4_XS | 0.0299 | 1.44 |
| qsa q | IQ4_XS | 0.0536 | 2.57 |
| qsa q | Q6_K | 0.0619 | 2.97 |
| shexp up | IQ3_S | 0.0160 | 0.77 |
| shexp gate | Q4_K | 0.0144 | 0.69 |
| shexp down | IQ4_NL | 0.0115 | 0.55 |
| router | BF16 | 0.0570 | 2.74 |
| **head** | Q5_K | **0.9206** | **×1 = 0.92** |

取 IQ4_XS 变体：单层 0.2655 ms ⇒ **48 层 = 12.74 ms + head 0.92 = 13.66 ms**，占 23 ms 的 **59%**。
`router_chain_bench` 独立复核：`mmvf+route+doorbell = 60.48 µs/层` × 48 = **2.90 ms**，
与上表 router 2.74 ms 同量级（不同实现，可互证）。

### 3.2 真正的靶心：GEMV 只跑到 22–75% 带宽（head 已 98%）

`q8_gemv_bench --cols 1 --bw 711`：

| 矩阵 | 大小 | µs | GB/s | 占带宽 |
|---|---|---|---|---|
| shared gate/up 2560→640 | 1.74 MB | 11.1 | 156.2 | **22%** |
| QSA k/v 2560→512 | 1.39 MB | 6.7 | 207.4 | **29%** |
| shared down 640→2560 | 1.74 MB | 7.7 | 224.8 | 32% |
| HC down 10240→320 | 3.48 MB | 14.0 | 248.1 | 35% |
| HC up 320→10240 | 3.48 MB | 13.8 | 251.6 | 35% |
| GDN gate 2560→6144 | 16.71 MB | 60.5 | 276.3 | **39%** |
| GDN qkv 2560→10240 | 27.85 MB | 68.8 | 404.8 | 57% |
| GDN/QSA out 6144→2560 | 16.71 MB | 34.0 | 491.5 | 69% |
| QSA q 2560→12288 | 33.42 MB | 62.9 | 531.6 | 75% |
| **head 2560→248320** | **675.43 MB** | **970.6** | **695.9** | **98%** |

- **head 已贴住带宽墙**（98%）⇒ 0.92 ms/token 是硬成本，别再打它。
- 其余 9 个矩阵合计 106.5 MB/层、279.5 µs/层 ⇒ ×48 = **13.42 ms**，加权只到 ~54%。
- **若全部提到 75%（533 GB/s）**：200 µs/层 ⇒ 9.6 ms，**省 3.8 ms/token**。
  换算到真实流量：decode 占 55.4% ⇒ **约 9.1% 的总时间**。这是目前算出来最大、且被实测支撑的一块。

**为什么低**：batch=1 的 GEMV，每层只有极少的 wave 可并行（MI50 60 CU），
小矩阵（1.4–3.5 MB）连一次完整 HBM 突发都填不满。方向是**提高单次调用的并行度**
（split-K / 更多 wave / dwordx4 向量化 / LDS 排布），正是 W835 台账里 G8（LDS padding）、
G9（DPP 归约）所指的同一类工作 —— 现在这两条**第一次有了量化靶心**：不是"可能有收益"，是"22% 到 75% 之间"。

---

## 4 hipBLASLt 格式转换：能转，语法层已通，收益上限 ≈ 0

> **改口径（AUDIT17 P1-5，2026-11-01 15:2x 由 W863 补）**：本节标题里的「收益上限 ≈ 0」原来是挂在
> §3 的 decode 占比数字上的（「瓶颈在 GEMV 带宽 22–75%，不是 GEMM」），而那组数字已作废（见头部横幅）。
> 结论 **DONE_NEG 仍然成立，但理由换结构性论证**：
> ① gfx906 的 ISA **没有矩阵指令**（W858 L4 已证）⇒ hipBLASLt 只能用 VALU kernel ⇒ 与 rocBLAS **同构**；
> ② non-MI codegen 的 17 个 `MI*` 字段在 TensileLite 里无人维护（W861 §5）⇒ 即便全通也不会比 rocBLAS 快，
> 且有**静默算错**的风险（那些字段参与偏移计算）。
> ⇒ 请把「收益上限 ≈ 0」读作「**结构等价 + 上游路径未维护**」，不要再挂任何性能数字。

### 4.1 逐层定位（三轮，每轮都推翻上一轮的假设）

| 轮 | 假设 | 实测 | 结论 |
|---|---|---|---|
| 1 | flow style（`- {K: V}`）导致 `parse_scalar` 断言失败 | `safe_load`+`safe_dump` 摊成 block 后**报错完全不变** | ✗ 不是 flow |
| 2 | `null` 值让 `k` 变 `None` 后错位 | 26 处 `null` 都在 **value** 位置，状态机正常 | ✗ 不是 null |
| 3 | **YAML 锚点/别名** | 原文件自带 **21 处** `ThreadTile: &id001` / `*id001`；`parse_general` 只处理 Mapping/Sequence/Scalar 三种 event，**遇 `AliasEvent` 返回 None 且不消费事件** ⇒ 状态机永久错位 | ✓ **真因** |

证据：`Dumper.ignore_aliases -> True` 展开后，`anchors left: 0`、`structure equal: True`，
**loader 不再报错**，TCL 进入下一阶段。

### 4.2 十三轮推进，每轮都前进一层（可复现的完整记录）

> 机主的判断是对的：**"上游没有 gfx906 logic" 这个问题早就在 W858 §10 解决了** ——
> 用的是 **rocBLAS 自己那份** `vega20_Cijk_Ailk_Bjlk_HHS_BH.yaml`（gfx906 + f16 + HPA，128 个解），
> 拿它反解出 config 并 codegen 成功。所以下面这些卡点都不是"没有 source of truth"，
> 是"把 rocBLAS 那批成熟解搬到 hipBLASLt 的新 schema"。

| 轮 | 报错 | 根因 | 修法 | 结果 |
|---|---|---|---|---|
| 1 | `parse_scalar` AssertionError | 以为是 flow style（`- {K: V}`） | 摊成 block style | **报错不变** ⇒ 假设错 |
| 2 | 同上 | 以为是 `null` 值 | 26 处 `null` 全在 value 位 | 不是它 |
| 3 | 同上 | **YAML 锚点**：原文件 21 处 `ThreadTile: &id001`；`parse_general` 只认 Mapping/Sequence/Scalar，遇 `AliasEvent` 返回 None **且不消费事件** | `ignore_aliases -> True` 展开 | ✅ loader 全通 |
| 4 | `missing required field matching property` | `parseLibraryLogicList` 要 12 元素，旧文件 9 个 | 补 `[9][10][11]` | ✅ 进入解析 |
| 5 | `KeyError: EnableMatrixInstruction` | `Solution.py:846` 推断完**没写回 state**，928 行直接读（gfx906 类非 MI 路径无测试） | 补 `False` | ✅ |
| 6 | `No valid DepthU found` | 缺 MX/subtile/metadata 一族字段，默认值让 GLVW 校验全线失败 | **`NoReject: True`** —— `Utilities.py::reject()` 第一行就认这个键，引擎自己留的口子，与 W858 §11.3 同一机制 | ✅ 不再打断 |
| 7 | `KeyError: ActivationComputeDataType` | 该键属 **ProblemType**，而 `ProblemType(...)` 构造时**没有** defaultSolution 兜底（Solution 有） | 让 `ProblemType(minimal, False).state` 自己吐 90 键当模板 | ✅ 37→90 键 |
| 8 | `Unknown assertion key: AssertMinApproxSize` | `Contractions.py::ProblemPredicate.FromOriginalKeyPair` 只认 3 类 Assert*，其余直接 raise | 剔掉废弃 Assert* | ✅ |
| 9 | `KeyError: ExpertSchedulingMode` | DefaultSolution 补齐仍不够 | 换思路：**用别的架构当模板**（见 11 轮） | → |
| 10 | `'int' object is not subscriptable` | `IsaVersion(isa[0],…)` 要三元组，我给 `ISA=906` | 删掉 ISA，交给 `gfxToIsa(arch)` | ✅ |
| 11 | **类型不匹配 545 处** | `DirectToLds`/`PrefetchGlobalRead`/`PrefetchLocalRead`/`UseSgprForGRO`/`VectorStore` 是 bool 但要 int；`Use64bShadowLimit` 反过来。msgpack 里两者 wire type 不同，会 `std::bad_cast` | 按 `validParameters` 的声明自动归一（不硬编码） | ✅ |
| 12 | `KeyError: NumLdsBlk` | `Solution.py:5522` 在 **MI 分支**里赋值，`KernelWriter._initKernel:7437` **无条件**读 —— non-MI 路径的 codegen 链在 2026 版是断的 | 补 `NumLdsBlk: 2` | 前进一层 |
| 13 | `KeyError: NumTotalPackedLoadsA` | 同一族的又一个 | —— | ❌ **判定此路不通** |

**第 13 轮的判断**：这不是"再补一个"，而是**一整族** `Num*` 字段都只活在 MI 路径。
2026 版 TensileLite 的 non-MI codegen 链已经无人维护（AMD 早已不在 gfx906/gfx900 上出
hipBLASLt kernel）。继续补是补不完的。

**但我们已经有一条成功路径**：W858 §11.3 走 **BenchmarkProblems**（`Tensile --cpu-only --build-only`）
产出了 `Actual Solutions: 1/1`、190 968 B 的 gfx906 ELF、63 条 `v_fma_mix_f32`。
所以缺的从来不是"能不能生成 kernel"，而是"库怎么被运行时认出来"。

### 4.3 改走另一条：关掉 lazy 加载，用已成功的非 lazy 库

`tensile_host.cpp:2805` 写着 `bool lazyLoad = ROCBLASLT_TENSILE_LAZY_LOAD;` —— **编译期宏，
运行期关不掉**；`2954` 的 else 分支才是 `TensileLibrary_<arch>.dat`（非 lazy）。
而 `CMakeLists.txt:89` 有 `option(HIPBLASLT_ENABLE_LAZY_LOAD … ON)`，`CMakeLists.txt:404`
把它传成 `ROCBLASLT_TENSILE_LAZY_LOAD=$<BOOL:…>`。

⇒ 自编 hipblaslt 时加 `-DHIPBLASLT_ENABLE_LAZY_LOAD=OFF`，就会去读 **非 lazy**
`TensileLibrary_gfx906.dat` —— 正是 gen16 已经产出的格式（`library.rows` + `solutions` 内联）。
不需要 Mapping.dat，也不需要把 logic 迁到新 schema。

（顺带确认：`LibraryIO.write()` 默认压缩，产物是 `.dat.zlib`，C++ 端会
`exists(.dat)` 或 `exists(.dat.zlib)` 二选一，两者都认。）

### 4.4 复现了 W858 §8.1 的缺符号，并用当时的方法修好

重编出来的库 `nm -D` 里 **`MessagePack` 符号 0 个、`LoadLibraryMapping` 为 `U`（undefined）**。
源码级根因在 `tensilelite/CMakeLists.txt`：

```cmake
if(HIPBLASLT_ENABLE_YAML)
    ... target_compile_definitions(... TENSILE_YAML)          # 只定义 YAML
else()
    ... target_compile_definitions(... TENSILE_MSGPACK)       # 才定义 MSGPACK
endif()
```

而 `TensileLite::LoadLibraryMapping` 的定义在 `#ifdef TENSILE_MSGPACK` 里
⇒ **开 YAML 编出来的库里它是 U**，一进库加载就崩。

按 W858 §8.1 的做法修：YAML 分支里额外补 `src/msgpack/MessagePack.cpp` + `-DTENSILE_MSGPACK`
（两条路径同时编进去）。重编后库从 10.0 MB 回到 **11.7 MB**（与上次成功的 11.743 MB 同量级），
`MessagePack.cpp.o` 出现在链接里。

> 顺带纠一个易踩的坑：`probe3` **不读** `HIPBLASLT_TENSILE_LIBPATH` 环境变量，
> 只认命令行第一个参数。日志里 `LIBPATH=(default, from the ROCm install)` 就是这个原因，
> 不是变量名错（变量名确实是 `HIPBLASLT_TENSILE_LIBPATH`，见 `tensile_host.cpp:2825`）。

### 4.5 终点一开始判错了：真因不是 comgr，也不是 gfx906

开 `AMD_COMGR_EMIT_VERBOSE_LOGS=1` 看到失败动作是
`AMD_COMGR_ACTION_COMPILE_SOURCE_WITH_DEVICE_LIBS_TO_BC`（OpenCL 1.2），
clang 24 不认 `--amdhsa-code-object-version=5` / `-amdgpu-prelink`。
我一开始据此判定"镜像级 comgr 缺陷、AMD 不修旧架构"，**这个判断是错的**。

**机主一句话点破**：ROCm 10.1 是支持 gfx906 的（rocBLAS 5.7 的 gfx906 表就在生产上跑）。
于是换 `LD_PRELOAD` 钩掉 `exit()` 抓 backtrace，真凶立刻现形：

```
libhipblaslt.so.1(hipblasLtCreate+0x6e)
libamdhip64.so.7(hipMemset+0x25)
libamd_comgr.so.3(amd_comgr_do_action)
libclang-cpp.so.24.0git(clang::ExecuteCompilerInvocation)
libhipblaslt.so.1(llvm::cl::ParseCommandLineOptions ...)   <-- 注意
exit(1)
```

**`llvm::cl::ParseCommandLineOptions` 落在了 `libhipblaslt.so.1` 里**。
因为 `tensilelite/CMakeLists.txt` 的

```cmake
if(HIPBLASLT_ENABLE_YAML)
    target_link_libraries(tensilelite-host PRIVATE LLVMObjectYAML)
```

把 **LLVM 静态链进了我们的库**；comgr 想用它自己那份 clang，却被**我们库里的 LLVM 符号抢先**
（ELF 符号插桩），参数版本对不上就在 `ParseCommandLineOptions` 里 `exit(1)`。

⇒ **`-DHIPBLASLT_ENABLE_YAML=OFF`（走纯 msgpack）后，`.so` 里
`ParseCommandLineOptions` 归零、体积从 11.7 MB 降到 8.40 MB**，随即：

```
hipblasLtCreate(&h)   status=0          ← 之前根本到不了这一步
LIBPATH=/v20/lib906                     ← 库路径被认
```

**这是整条线最关键的一步**：不是环境不行，是我们自己的构建选项引入了符号冲突。

### 4.8 client 编成了 —— 三个"缺件"其实两个是路径问题

`mxDataGenerator` 看起来是过不去的硬依赖，实际拆下来只有**一个真缺件**：

| 报错 | 真因 | 修法 |
|---|---|---|
| `mxDataGen.hpp file not found` | 这个头**就在树里**：`clients/common/include/mxDataGen.hpp`，只是 client 的编译命令里**没加这个 include 目录** | CMake 加 `-I/src/projects/hipblaslt/clients/common/include` |
| `mxDataGenerator/*.hpp`（6 个 ocp_* 头） | 只被 `DataInitializationHelpers.hpp` 引用，而 client 的编译单元**没走到那个头** | 无需处理，实际没编到 |
| `undefined symbol: mxScaleLayoutForArchName` | 实现在 `clients/common/src/mxDataGen.cpp`（那个文件才依赖 DGen），但**函数本身只有 8 行、零外部依赖** | 写 `mx_stub.cpp` 只提供这一个函数；gfx906 落到 `MXScaleLayout::None`（本来就没有 MX 缩放布局） |

结果：**`tensilelite-client` 编成，12 016 552 B**。

过程中还踩了 CMake 语法坑：`add_library(tensilelite-client-common STATIC)` 后面**不能直接跟源文件名**（括号已闭合），
必须用 `target_sources(...)`。

⇒ 之前判定的"缺兄弟仓库源码"**是误判**。`mxDataGenerator` 只在 MX 数据生成路径上需要，
而 gfx906 + f16 的 benchmark 完全用不到它。

`--build-only` 会 **"skipping LibraryLogic"**，所以真 benchmark 必须编 `tensilelite-client`。
配置阶段连撞两次，根因都很具体：

| 现象 | 根因 | 修法 |
|---|---|---|
| `add_subdirectory(.../shared/mxdatagenerator) which is not an existing directory` | 开关名是 **`HIPBLASLT_ENABLE_MXDATAGENERATOR`（全大写）**，我一直传小写 `hipblaslt_...`，CMake 变量**大小写敏感** ⇒ OFF 从未生效 | 改全大写后 **cfg rc=0、0 error** |
| `hipblaslt-mxdatagen links to roc::mxDataGenerator` | 该 target 在 `clients/common` 里是**无条件**声明 | 用开关把 23 行包起来（`_W861_MXDATAGEN_GUARD`） |

配置通了之后，编译 `tensilelite-client` 才露出**真正的硬依赖**：

```
tensilelite/client/include/DataInitialization.hpp:37:  #include <mxDataGen.hpp>        ← 无条件
tensilelite/client/include/DataInitializationHelpers.hpp:9-14:
    #include <mxDataGenerator/dataTypeInfo.hpp>
    #include <mxDataGenerator/ocp_e2m1_mxfp4.hpp>  … 还有四个
```

`mxDataGenerator` 是 hipBLASLt 的**兄弟仓库**（本树里没有 `shared/mxdatagenerator`），
client 的 `DataInitialization` 无条件包含它的一整套头，**不是开关能关掉的**。
造 stub 要覆盖 `generateMXInput` + 六个 `DGen::ocp_*` 类型，工作量超过收益。

镜像里 `amd_smi` 是齐的（头 + `libamd_smi.so.27`），所以 client 只差这一个组件。

现在 `hipblasLtCreate status=0`、`LIBPATH=/v20/lib906` 被认、无 `Cannot derive arch`、
无 `No library mapping`。`TENSILE_DB=0xffff` 把最后一层点名：

```
Unknown key hardwarePredicate
(合法键: taskPredicate, problemType, name, kernelName, internalArgsSupport,
 libraryLogicIndex, index, sizeMapping, problemPredicate, ideals, linearModel, debugKernel)
```

**gen16 那份库带着 benchmark 阶段的 `hardwarePredicate`，运行时库不认** ——
所以 `algos=0` 的真因不是 predicate 匹配，而是 **solution 一个都没解析进库**。

已排除：

| 检查 | 结论 |
|---|---|
| `problemPredicate` 放宽到"类型对就给解" | 不是它 |
| compute 16F vs 32F | 不是它 |
| `hardwarePredicate` 换 `{type:True}` / 直接删掉 | 加载直接失败 ⇒ 必须原样保留 |
| LAZY_LOAD=OFF + 非 lazy 库 | 上游硬检查要求文件名以 `TensileLibrary_lazy_` 开头（`MasterSolutionLibrary.hpp:132`），此路必挂 |
| lazy 子库布局 | 按 `PlaceholderLibrary.hpp:165` 的 `libraryDirectory + "/" + filePrefix + suffix` 规则，我们的布局正确 |
| 写出的库文件 | 解压后 **无** `hardwarePredicate` 字符串、**有** `taskPredicate`（已验证） |

⇒ **剩一个"读到的是哪个文件"的问题**：文件本身已干净，报错仍在，说明还有一份同名库被读到
（容器内默认搜索路径或残留副本），或者解析发生在写回前的某个中间态。下一步就是定位这份文件。

---

## 5 llama.cpp 依赖：纪律修正（机主两次纠正）

上一轮编 `fused_gr_bench` 时 cmake 重配失败于 `add_subdirectory /llama.cpp/ggml`，
我当时的反应是"绕开 cmake、touch build.ninja、直接 hipcc"。**这是错的**——
机主问"llama.cpp 不是 166 上现成的吗"，一查就在：

```
/home/albus/strata166/src028/third_party/llama.cpp   （166 M，ggml/include/ggml.h 齐全）
```

（我第一次 `find -maxdepth 3` 漏了它，深度是 4。）

**挂上去一次通过，`cmake --build` 2.5 分钟编完 61/61 步。** 纪律：

> 构建失败先找**依赖在哪**，再考虑绕开构建系统。`gfx029-build/CMakeCache.txt` 里的
> `STRATA_GGML_DIR:PATH=/llama.cpp` 早就写明了它要什么，读 cache 比猜快。

---

## 6 日志挖掘：三个"看起来像故障"的东西都不是当前故障

| 现象 | 条数 | 真相 |
|---|---|---|
| `verify: timed out at layer 2 ... within 5 s (#267)` | 5 | **rocprofv3 抓 profile 造成**。同段落里是 `queue_interposition.cpp:374 Async signal handler still waiting` 和 `rocprofv3 caught signal 15`，日期 10-24。⇒ **别在生产上随手 rocprof** |
| `decode waited 5529.0 ms in 9762 fetches` | 44（>5 s） | 全部落在 **10-21 的某个版本**（每条前后都有 `engine started 2026-10-21`），与当前 0.2.9-101 无关。常态是 414/458 条 = 0 ms |
| `resident RAM: 33.44 GiB of experts in RAM` | — | 不是异常：**专家本来就走 mmap + host RAM + CPU AVX2**（`experts via mmap`、`the expert kernels run on AVX-2`）。GPU 只放 dense 2975 MiB + MTP 1098 MiB |

⇒ 没有"当前正在拖慢"的故障。**慢是结构性的，不是坏的。**

---

## 7 本轮建起来的工具链（都可复用，全零干扰）

| 脚本 | 用途 | 状态 |
|---|---|---|
| `albus/w861/time_weight.py` | 真实流量的**时间加权**分档（不是条数加权） | 已跑 |
| `albus/w861/decode_split.py` | decode ms/token 二维分桶（prompt × gen） | 已跑（acc% 列有 group 错位，需修） |
| `albus/w861/convert_logic.py` / `convert_logic2.py` | 旧 logic → block style / 展开锚点 | 已验证 |
| `albus/w861/dbg_loader.py` | 回放 `CustomYamlLoader` 事件流，定位加载失败 | 已验证 |
| `albus/w861/sampler.sh` | 每秒 CPU/GPU 采样（等真实请求时抓 decode 占用） | 运行中 1 h |
| `albus/w861/bench_build2.sh` | 逐个编 bench，一个失败不拖垮全批 | 6/8 成功 |

已编出的可执行（`gfx029-build/`）：`fused_gr_bench`、`b6_mmvq_bench`、`q8_gemv_bench`、
`router_chain_bench`、`native_expert_bench`、`qsa_rows_bench`、`gfx906_qsa_query_swizzle_probe`。
（`gdn_chunk_bench` 在 gfx906 构建里不存在；`mmq_expert_bench` 还没编完。）

---

## 8 下一步（按 §1 的新账重排）

| 序 | id | 内容 | 判据 | 干扰 |
|---|---|---|---|---|
| **1** | **R22** | decode dense GEMV 带宽 22–75% → 75%（split-K / wave 并行 / dwordx4） | 微基准：单层 279.5 µs → 200 µs；总量 9.1% | 微基准零干扰，落产需停服 |
| 2 | R21 | hc read 19.2%（prefill 内第二大项） | v1 vs v3 微基准 | 零干扰 |
| 3 | — | prefill 64K+ 档（read 的 41%）：gemm gate/up 20% + hc read 19.2% + wait copy 13.8% | 相位表 | 停服 |
| — | ~~R19~~ | 短档固定开销 | **降级**：只占 1.2% read 时间 | — |
| — | ~~M3~~ | int8 KV | **降级**：decode 不随 ctx ⇒ 不在 KV | — |
| — | ~~X17~~ | hipBLASLt | **DONE_NEG**（§4） | — |
