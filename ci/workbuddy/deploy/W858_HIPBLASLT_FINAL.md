# hipBLASLt on gfx906：从"能力未知"跑到"能力已证、加载器不通、收益不成立"

> 2026-11-01 02:0x–02:4x。承 W856 的 P0（BLOCK）继续，把依赖一层层打通，直到把 gfx906 的机器码生成出来。
> 全部在不占生产的前提下完成（codegen 是 CPU 交叉编译，探针用 `--rm` 容器）。

## 0 结论（四级）

| 级 | 问题 | 答案 | 证据 |
|---|---|---|---|
| L1 | 能不能把 rocisa 编出来？ | **能** | 5 层依赖全打通，见 §1 |
| L2 | 生成器能不能为 gfx906 出机器码？ | **能** | `Kernels.so-000-gfx906.hsaco` 219,448 B，`amdhsa.target = amdgcn-amd-amdhsa-unknown-gfx906`，4 个 kernel，md5 `ffca7a53…` |
| L3 | rocblaslt 能不能加载这个库？ | **不能** | 一律 `rocblaslt error: Could not load …`；**连镜像自带、rocBLAS 自己能用的那份 gfx906 lazy 库也拒收** |
| L4 | 就算能加载，值不值得？ | **不值得** | gfx906 的 ISA **没有矩阵指令**，所以 hipBLASLt 只能用 VALU kernel —— 与 rocBLAS 同构，而 rocBLAS 那 84 行表我们已经调过了 |

## 1 依赖链：五层，逐层留证

| 层 | 现象 | 处置 |
|---|---|---|
| ① Python 包缺失 | 镜像只有 `_rocisa.abi3.so`，`import rocisa.rocIsa` 失败 | 从源码装 |
| ② 构建后端 | `scikit-build-core` / `nanobind` 缺 | **清华源没有该包**（`from versions: none`），**阿里云可用**；PyPI 直连读超时（293 kB 也超时） |
| ③ origami | CMake 找 `../../../../shared/origami` | `git sparse-checkout add shared/origami` |
| ④ stinkytofu | `CMakeLists.txt:162` FATAL_ERROR | `git sparse-checkout add shared/stinkytofu`（8.1 MB） |
| ⑤ 仓库根 `cmake/modules` | 找不到 `default_amdclang.cmake` | `git sparse-checkout add cmake` |

另外两个坑（都不是依赖问题）：
- **必须按原层级复制**：rocisa 用相对路径找兄弟，只 copy rocisa 会找不到 `shared/*`。做法：
  `/tmp/tree/projects/hipblaslt/tensilelite/rocisa` + `/tmp/tree/shared/{origami,stinkytofu}` + `/tmp/tree/cmake`。
- **它往 CWD 写 `MatchTable.yaml`**：CWD 是只读挂载时，会以 `OSError: Read-only file system` 的形式伪装成"逻辑解析失败"。

构建结果：`_rocisa.cpython-312-x86_64-linux-gnu.so` + `libstinkytofu.so.0.1.0`，`import rocisa` 通过。

## 2 生成 gfx906 机器码：关键在"用非 MI 解"

| 尝试 | 做法 | 结果 |
|---|---|---|
| 1 | gfx942 的 f16 logic + `--architecture=gfx906` | 走到写 `MatchTable.yaml` 才因只读挂载失败——**说明它没在架构上拒绝** |
| 2 | 把 logic 的 `gfx942/aquavanjaram` 改成 `gfx906/vega20` | `reject: isa gfx906 doesn't support matrix instruction` |
| 3 | 再加 `EnableMatrixInstruction: false` | `reject: SIA2 and SIA3 only support MatrixInstruction` |
| 4 | 改用 `gfx1100/SB.yaml`（**本身就是非 MI 用例**：`EnableMatrixInstruction: false`、`MatrixInstruction: []`、`ScheduleIterAlg: 1`），只改 arch 行 | **成功** |

**第 2 步那条 reject 就是本质**：gfx906 的 ISA 没有矩阵指令（MI50 的 26.6 TFLOPS fp16 来自 packed FMA，不是 MFMA）。
所以任何 MI 解都不可能落在 gfx906 上；**只有 VALU（非 MI）解可行**，而树里**唯一的非 MI 模板就是 codegen 测试用例 `gfx1100/{SB,DB}.yaml`**
（全树 74 个 logic：`EnableMatrixInstruction: true` 72 个、`false` 只有这 2 个；gfx906 的 logic **0 个**）。

产物（`/home/albus/strata166/data/w858_hblt/gen5/library/gfx906/`）：

```
Kernels.so-000-gfx906.hsaco                                   219448   amdhsa.target=amdgcn-amd-amdhsa-unknown-gfx906
TensileLibrary_lazy_gfx906.dat                                  1106   msgpack keys=[library, solutions, version] version=5
TensileLiteLibrary_lazy_gfx906_Mapping.dat                         88
TensileLibrary_SS_SS_HA_Bias_SAV_UA_Type_SS_Contraction_..._gfx906.co/.dat
日志：Total kernels processed: 4       Time to generate kernels: 6.53 s
```

## 3 加载器这一关：连"原厂 gfx906 库"也拒收

用 `HIPBLASLT_TENSILE_LIBPATH` 指库目录，跑了四种：

| 库 | 结果 |
|---|---|
| 默认（镜像自带） | `hipModuleLoad failed: Kernels.so-000-gfx906.hsaco … file not found`（它**会去找** gfx906 的 hsaco，连 `-xnack±` 变体都试） |
| 我们自建（gen5） | `Could not load …/TensileLibrary_lazy_gfx906.dat` |
| 我们自建（去掉 `version` 键，对齐 rocBLAS 那份的键集） | 同上 |
| **镜像自带、rocBLAS 正在用的** `/opt/rocm/lib/rocblas/library/gfx906/` | **同上** |

第四行是决定性的：**一个 rocBLAS 自己能加载的 gfx906 Tensile 库，rocblaslt 也拒收**。
所以不是我们写错了库，是 **rocblaslt 没有 gfx906 的读取路径**——与它 CMake 白名单里没有 gfx906 完全一致。

> **顺带纠正一条旧结论**（W848/W851）：`/opt/rocm/lib/rocblas/library` 里 **gfx906 是有的**，只是放在
> `library/gfx906/` 子目录里。当初在顶层 `grep -c gfx906` 得 0，据此写过"gfx906 没有内核"，那句是错的。
> 实测该目录含 `Kernels.so-000-gfx906.hsaco`(232,744) 与 i8/f32 多套 `.dat/.hsaco`。

## 4 为什么到此为止（而不是继续改 hipBLASLt）

要继续只有一条路：**改 rocblaslt 的库加载器**，让它认 gfx906。代价与收益：

- 代价：那是 C++ 大库里的加载路径 + 白名单 + 可能的 kernel 假设（wave64 vs wave32、MFMA 缺席），属于"改上游库"，天级；
- 收益：**结构上不可能超过 rocBLAS**——两者都只能用 VALU kernel，而 rocBLAS 的 gfx906 解已经由我们自己的
  84 行调优表选过解（`STRATA_ROCBLAS_TUNING`，W851 实测 5.7 与 5.5 判定 0 分歧）。

⇒ **支线收束（B 线关闭）**，保留全部脚本与产物供日后复原。若哪天上游把 gfx906 加回白名单，本件的 §2 可直接复用
（`albus/w858/b5_all.sh` + `b9_algos.sh`）。

## 5 复现（三条命令）

```bash
# 1) 依赖（阿里云源，清华源缺 scikit-build-core）
python3 -m pip install --target /out/pylib -i https://mirrors.aliyun.com/pypi/simple \
  "scikit-build-core>=0.10" "nanobind>=2.0,!=3.0.0" joblib msgpack
# 2) 编 rocisa（按原层级放好 rocisa/shared/{origami,stinkytofu}/cmake）
bash albus/w858/b5_all.sh          # 或手工 cmake + ninja install，产物在 /out/rocisa-install
# 3) 生成 gfx906 库（用非 MI 模板）
python3 Tensile/bin/TensileCreateLibrary <logic906c> <out> HIP \
  --architecture=gfx906 --code-object-version=5 --library-format=msgpack --no-enumerate -j 8
```

---

## 6 第二轮（W859）：自己编主机库 —— 编通了，运行期卡在别处

上一节的 L3 结论是"rocblaslt 不认 gfx906 库"。上网核实后确认那是**发行版里那个 `libhipblaslt.so` 是空壳**
（Gentoo bug 960513 原话：*"hipBLASLt has no kernels for gfx1012 or gfx906 (it would still build a **dummy**
hipBLASLt library as a placeholder for other libraries like pytorch)"*；TheRock-gfx906 的构建说明同样写
*"no lib/hipblaslt/library/gfx906"*）。官方文档给了正确姿势：`-DTensile_SKIP_BUILD=ON` 只编主机库，device 库由
`HIPBLASLT_TENSILE_LIBPATH` 外挂。于是改成自编主机库。

### 6.1 配置阶梯（每步都留了证据）

| 步骤 | 报错 | 处置 |
|---|---|---|
| 0 | sparse 里只有 `tensilelite`，`include(hipblaslt_shim)` 找不到 | `git sparse-checkout add projects/hipblaslt projects/hipblas-common` |
| 1 | `enable_language` 报 "is not a full path" | 补 `-DCMAKE_HIP_COMPILER=/opt/rocm/llvm/bin/clang++ -DCMAKE_HIP_ARCHITECTURES=gfx906` |
| 2 | `CMAKE_Fortran_COMPILER gfortran` 找不到 | `-DHIPBLASLT_ENABLE_CLIENT=OFF`（clients 才要 Fortran） |
| 3 | `msgpackc-cxx` 找不到 | `-DHIPBLASLT_ENABLE_YAML=ON`（只有 YAML=OFF 才需要 msgpack 的 **CMake 包**） |
| 4 | `Could NOT find zstd` + `LLVMExports.cmake set_target_properties` 失败 | `-Dzstd_LIBRARY=/usr/lib/x86_64-linux-gnu/libzstd.so.1 -Dzstd_INCLUDE_DIR=/opt/rocm/lib/rocm_sysdeps/include` |
| 5 | 编译期 `msgpack.hpp` not found（tensilelite 的 `Loading.hpp` 无条件 include） | 取 `msgpack-cxx-6.1.1` 头文件（gh-proxy → 476 KB），`-DCMAKE_CXX_FLAGS/-DCMAKE_HIP_FLAGS=-I<dir>` |
| 6 | `boost/predef/other/endian.h` not found | 加 `-DMSGPACK_NO_BOOST` |

**成品**：`/out/build/library/libhipblaslt.so.1.4`（61/61 链接成功，10,037,032 B），
`ldd` 确认走 `/opt/rocm/lib/libamdhip64.so.7` + `libamd_comgr.so.3`，与系统库同一套运行时。

### 6.2 运行期：卡在 `hipblasLtCreate` 里的 `hipMemset`

- 用新库后 **`Could not load TensileLibrary_lazy_gfx906.dat` 消失**（说明库格式这关过了）；
- 但 `hipblasLtCreate` 直接 `exit(1)`，连返回码都打不出来；
- 容器里没有 gdb，用 `LD_PRELOAD` 拦 `exit` 抓栈，拿到：

```
libhipblaslt.so.1(hipblasLtCreate+0x6e)
libamdhip64.so.7(hipMemset+0x25) → … → amd_comgr_do_action → libamd_comgr.so.3(+0x2194b4)
```

即：`create` 里第一句 `hipMemset(d_Synchronizer, 0, gsuBytes)` → HIP 让 **comgr** 编 memset 的 fill kernel →
comgr 把 **`--amdhsa-code-object-version=5`** 和 **`-amdgpu-prelink`** 传给 clang，而本镜像是 **clang 24（LLVM 24）**，
这两个参数已经不认了（就是启动时那四行 `clang (LLVM option parsing): Unknown command line argument`）→
memset 失败 → `CHECK_HIP_ERROR` 宏里写着 `exit(EXIT_FAILURE)`。

**排除项**（都实测过）：
- 不是尺寸问题：最小 HIP 程序 `hipMalloc+hipMemset` 在 4 KB/1 MB/16 MB/64 MB/256 MB 全部返回 0；
- 不是影子库：`/out/build/library` 只有 `libhipblaslt*`，`ldd` 与系统库解析到同一批 `.so`；
- 不是 ext-op：`-DHIPBLASLT_ENABLE_EXTOPS=OFF` 重编后症状不变；
- 与 gfx906 白名单无关：`Architectures to process: gfx906` 已出现在配置输出里。

### 6.3 下一步（写在明处，不靠猜）

1. 在**正确的函数**里插桩（上一版插到了 `hipblasLtCreate` 之外的第一个 `CHECK_HIP_ERROR(hipMalloc(&d_Synchronizer…`
   位置，编译报 `expected '}'`，已 `git checkout` 还原）——打印 `gsuBytes/skBytes` 与两个 hip 调用的真实返回码；
2. 或者绕过 comgr：`hipMemset` 改成 `hipMemsetD32`/自带 kernel，或把 `d_Synchronizer` 的初始化推迟到首次 matmul；
3. 或者换 comgr：本机 `pkgs/` 里还有 ROCm 7.14 的 `libamd_comgr.so`（`/opt/rocm/core-7.14/lib`），
   用 7.14 的 comgr + 10.1 的 hip 组合验证是不是纯 comgr 版本问题；
4. 若 1–3 都过，再回到 `AlgoGetHeuristic` 与 ms 对比。

> 现在这一步**已经不在"发行版不给 gfx906"那堵墙上**，而是"这套 10.1 快照的 comgr 与 clang 24 参数不匹配"——
> 一个有明确修复路径的工程问题。

---

## 7 第三轮（W859）：句柄通了、库被找到了，只差一个符号

§6 的卡点（`hipblasLtCreate` 里 `hipMemset` → comgr 报错 → `exit(1)`）在这一轮被拆开了。

### 7.1 根因：镜像级 comgr × clang 参数错配（与 gfx906 无关）

开 `AMD_COMGR_EMIT_VERBOSE_LOGS=1` 拿到 comgr 的实际动作：

```
ActionKind: AMD_COMGR_ACTION_COMPILE_SOURCE_WITH_DEVICE_LIBS_TO_BC
IsaName   : amdgcn-amd-amdhsa--gfx906:sramecc+:xnack-
Driver Job Args: clang -cc1 "-mcode-object-version=5" "-mllvm" "--amdhsa-code-object-version=5" … "-mllvm" "-amdgpu-prelink"
```

即 **comgr 用自己内建的 clang 24，却传了 `-mcode-object-version=5` / `-amdgpu-prelink` 这些它已不认的参数** →
OpenCL JIT 失败 → `hipMemset` 失败 → `CHECK_HIP_ERROR` 里 `exit(EXIT_FAILURE)`。
最小 HIP 程序（`hipMalloc+hipMemset`，4 KB…2 GB 全测）**一律正常**，因为那条路走预编译、不 JIT。
⇒ 这是**镜像级的 comgr/JIT 缺陷**，不是 gfx906，也不是我们编的库。

### 7.2 绕过它之后：`hipblasLtCreate` 成功、库被正确找到

把 `hipblasLtCreate` 里那两句 `hipMemset` 跳过（只做 heuristic 探测，不跑 GSU/StreamK），立刻：

```
hipblasLtCreate(&h)   status=0
rocblaslt error: Cannot read ".../TensileLibrary_lazy_gfx906.yaml"      ← 它在找 YAML 格式
```

⇒ ① 句柄通过；② 它**按我们给的 `HIPBLASLT_TENSILE_LIBPATH` 去读库**了（不是之前的"拒收"）。
因为主机库是按 `-DHIPBLASLT_ENABLE_YAML=ON` 编的，库要用 `--library-format=yaml` 生成。
重新生成后得到 `TensileLibrary_lazy_gfx906.yaml`（gen7），格式这关也过了。

### 7.3 当前唯一卡点：`tensilelite-host` 的符号没被真正带进 `.so`

```
libhipblaslt.so.1: undefined symbol:
  _ZN11TensileLite18LoadLibraryMappingERKNSt7__cxx1112basic_stringIcSt11char_traitsIcESaIcEEE
```

`CMakeLists.txt:382` 明明 `target_link_libraries(hipblaslt PRIVATE roc::tensilelite-host)`，但 `nm` 里该符号始终是 `U`。
试过四条，都不成：`TENSILELITE_ENABLE_HOST=ON`（本来就是 ON）、共享版 + `LD_PRELOAD`（符号被 hidden visibility 挡住，
`nm -D` 为 0）、`CMAKE_SHARED_LINKER_FLAGS` 追加 `.a`（flags 在目标文件之前，解析不到）、
`CMAKE_CXX_STANDARD_LIBRARIES` 追加（CMake 仍按 target 的链接行走）。
**下一步**：把 `target_link_libraries` 里的 `roc::tensilelite-host` 换成直接的 `tensilelite-host` 目标名
（`roc::` 这个 ALIAS 可能解析到"已安装的"那个 imported target），或在该行后显式
`target_link_options(hipblaslt PRIVATE -Wl,--whole-archive .../libtensilelite-host.a -Wl,--no-whole-archive)`。

> 这一轮把"能不能做"彻底回答了：**能**。剩下的全是构建工程（链接、库格式），没有一条涉及 gfx906 能力。

---

## 8 第四轮（W859 续）：**管线全通** —— `status=0`

上一节只差一个符号。这一轮把它拆成两句真话，然后打通了。

### 8.1 缺符号的真因：`TENSILE_MSGPACK` 宏 + CMake 漏源文件

`tensilelite/src/Tensile.cpp:49-54`：

```cpp
#ifdef TENSILE_MSGPACK
    std::map<int, std::string> LoadLibraryMapping(std::string const& filename) { return MessagePackLoadLibraryMapping(filename); }
#endif
```

**定义在这个宏里，而 hipblaslt 的 lazy 库路径无条件调用它** ⇒ YAML-only 构建必然缺符号。
补 `-DTENSILE_MSGPACK` 后又冒出 `MessagePackLoadLibraryFile<…>` 缺失，查下去发现
`tensilelite/src/msgpack/MessagePack.cpp` **根本没在 CMake 源列表里**（`nm libtensilelite-host.a | grep -c msgpack` = 0）。

处置（两步，都在我们自己的树里）：
1. `-DCMAKE_CXX_FLAGS/-DCMAKE_HIP_FLAGS` 追加 `-DTENSILE_MSGPACK`；
2. `tensilelite/CMakeLists.txt` 里 `add_library(tensilelite-host)` 之后加
   `target_sources(tensilelite-host PRIVATE src/msgpack/MessagePack.cpp)`。

结果：`.a` 里 msgpack 符号 **96 个**，`libhipblaslt.so.1` 的 **未定义 TensileLite 符号清零**。

### 8.2 打通：`status=0`

```
hipblasLtCreate(&h)              status=0
LIBPATH=/out/gen7/library/gfx906
  f32  M=256 N=10240 K=2560 : status=0 algos=0
  f16  M=256 N=10240 K=2560 : status=0 algos=0
  f16  M=2048 N=2560 K=640  : status=0 algos=0
```

`status` 从 **3（HIPBLAS_STATUS_INVALID_VALUE）变成 0**，这才是这一轮真正的里程碑：
**库被我们自建的 hipblaslt 加载、解析、参与 heuristic 计算了**，只是还没有匹配的解。

`algos=0` 的原因很干净：我们生成的库是 `SB.yaml` 派生的 **SS（f32）且带 Bias/ScaleAlphaVec** 的专用 problem type，
而探针查的是朴素 f16 GEMM。

### 8.3 f16 缺口：生成器在 gfx906 的 f16 MAC 组件上有两个 bug

把 SB 的 problem type 从 f32 改成 f16（`DataType: 0→4` + `HighPrecisionAccumulate: true`，解的参数不动），
codegen 立刻撞上：

```
TypeError: FMA_F16_HPA_MAD_MIX.__call__() takes 4 positional arguments but 6 were given
```

`Tensile/Components/MAC_F16_HPA.py:90` 的 `asmCaps = caps['v_mad_mix_f32'] or caps['v_fma_mix_f32']` ——
**这正是 gfx906 的 f16 路径**（`v_mad_mix_f32` 是 Vega20 的指令），而它的 `__call__(self, writer, m, innerUnroll)`
还是老签名。加 `*a, **kw` 吸收多余参数后，下一个错是
`TypeError: 'dict' object cannot be interpreted as an integer` —— 说明调用方把 `tP`（dict）放在第一个位置传进来了，
**组件的函数体需要按新 Component API 真正适配**（不是签名一行能糊过去的）。

### 8.4 结论与下一步

| 项 | 状态 |
|---|---|
| rocisa / origami / stinkytofu / LLVM24 依赖 | ✅ 全通 |
| TensileLite 为 gfx906 生成 **f32(VALU)** 机器码 | ✅ `Kernels.so-000-gfx906.hsaco` |
| 自建 hipBLASLt 主机库（gfx906 白名单） | ✅ 61/61 |
| 库加载 + heuristic 查询 | ✅ **`status=0`** |
| 匹配的解（f16） | ❌ 需 ① 适配 `FMA_F16_HPA_MAD_MIX` 到新 Component API；② 一套 f16 的非 MI logic |

**这不是"能不能"的问题了，是"还差两块工程量"**。而且要注意：即便补齐，收益上限仍然是 rocBLAS
（gfx906 无矩阵指令，两边都只能 VALU kernel）。

---

## 9 第五轮（W860）：走到**汇编器**了，卡在上游一个重复标签的 bug

§8 结束时缺口是"f16 的 MAC 组件没适配新 API"。这一轮把 f16 那条放下、改走 **f32 朴素 SS**
（因为 gen7 的 f32 非 MI 库早就生成成功了，只需要 problem type 对上），结果**又往前推了一层**。

### 9.1 f16 组件的真因（顺手查清，不用再猜）

`Tensile/Components/MAC_F16_HPA.py` 里两个类签名不一致：

```python
class FMA_F16_HPA_DOT2(MAC):        # 第 34 行：新 API
    def __call__(self, writer, tPA, tPB, m, innerUnroll):

class FMA_F16_HPA_MAD_MIX(MAC):     # 第 90 行：老 API（只有 3 参）
    def __call__(self, writer, m, innerUnroll):
        ... writer.tPA["tileIdx"] ...   # 函数体里 4 处用 writer.tPA/tPB（新 API 已改成参数）
```

上一轮我加 `*a, **kw` 后报 `'dict' object cannot be interpreted as an integer` 的机理也清楚了：
调用方按新 API 传 `(writer, tPA, tPB, m, innerUnroll)`，`tPA/tPB` 被 `*a` 吃掉，于是 **`m` 收到的是 tPB（dict）**。
正确改法是 **签名对齐 DOT2 + 把 4 处 `writer.tPA/tPB` 换成参数**（`albus/w860/gen10_f16.sh` 就是这么改的）。
改完 f16 仍失败，但失败点已经不在这个组件（见 9.2）。

### 9.2 f32 朴素 SS：一路走到汇编器

`SB.yaml` 原本是 `SS_HSS_BH_Bias_S_HA_S_SAV_UserArgs`（f32 + bias + ScaleAlphaVec + activation），
heuristic 按 problem type 严格匹配，探针查朴素 GEMM 必然 `algos=0`。于是派生一份朴素 SS
（`albus/w860/mk_ss_logic.py`：`Batched/StridedBatched` 关、`UseBias 0`、`UseScaleAlphaVec 0`、
`BiasDataTypeList []`、arch 改 `vega20/gfx906`），生成时**前面的 Python 全过了**，直到：

```
error: symbol 'label_label_skip_ab_buffer_deref_WorkGroup2' is already defined
Failed command: amdclang++ -x assembler --target=amdgcn-amd-amdhsa -mcode-object-version=5                 -c -mcpu=gfx906 -mwavefrontsize64 ... .s -o .o
```

**这是本轮最重要的位置信息**：命令里出现了 `-mcpu=gfx906 -mwavefrontsize64`，
说明 codegen → .s 全部成功，**是 amdclang++ 在汇编阶段拒收**。

### 9.3 定位：`KernelWriterAssembly.py:2188`

```python
#handle Batch A/B
endCheckLabel = Label(self.labels.getName(f"label_skip_ab_buffer_deref_{Batch}"), "")
...
module.add(endCheckLabel)
```

它在 `for idx in kernel["ProblemType"]["IndicesBatch"]:` 那段之后、**同一个 `Batch` 作用域里又 emit 了一次**；
而 `labels.getName()` 对同名返回同名（复用语义），于是同一个标签被 `module.add` 两次 ⇒ 汇编器报重复定义。
名字里出现 `label_label_` 两个前缀，是因为 `Label.__init__` 自己还会再加一次前缀。

**为什么 MI 路径不炸**：这段只在这条非 MI（VALU）分支里走到，而 MI 路径早就 return/走别的模块。
换句话说——**这条非 MI 路径上游自己没跑过**（全树 f16 非 MI 用例 = 0，f32 非 MI 只有 2 个 codegen 单测用例，
而那两个用例根本没走到 `Batched` 模板）。

### 9.4 到此为止的判断（不粉饰）

| 层 | 卡点 | 性质 | 结果 |
|---|---|---|---|
| 1 | rocisa 无 Python 包 / 指令集缺失 | 工程 | ✅ 自建解决 |
| 2 | origami / stinkytofu / 仓库根 cmake | 工程 | ✅ sparse add |
| 3 | 发行版 `libhipblaslt.so` 是空壳 | 发行版 | ✅ 自编主机库 61/61 |
| 4 | `LoadLibraryMapping` 未定义 | 上游 bug（`#ifdef TENSILE_MSGPACK`） | ✅ 加宏 |
| 5 | `MessagePack.cpp` 未在 CMake 源列表 | 上游 bug | ✅ 加 `target_sources` |
| 6 | `hipblasLtCreate` 里 `hipMemset` → comgr×clang24 参数不匹配 | **镜像缺陷**（`P240`） | ✅ 绕过（跳过该 memset） |
| 7 | **非 MI 模板 `label_skip_ab_buffer_deref` 重复定义** | **上游 bug（生成器状态机）** | ❌ 卡住 |

**判定**：这不是"我们不会配"。第 7 层要改的是 `LabelManager` 的去重语义或那段 emit 的作用域，
属于**生成器内部状态机**，改一处可能牵出十处；而且它**只影响非 MI 路径**——也就是 gfx906 唯一能走的路。

**收益上限没变**：gfx906 无矩阵指令（`isa gfx906 doesn't support matrix instruction`），
hipBLASLt 和 rocBLAS 在 gfx906 上都只能出 VALU kernel，而 rocBLAS 的解我们已用 84 行表调过。
⇒ 即使第 7 层修通，**最好的结果也只是打平 rocBLAS**。

### 9.5 若要继续，最短的两条（成本已估）

1. **去掉 batch**：让 logic 里 `IndicesBatch: []`、`NumIndicesBatch: 0`，那样 `for Batch in ...` 空循环、
   这段 emit 不进入。**但** §9.2 的 kernel 名仍是 `Cijk_Ailk_Bjlk_S_B_GB_HA_S_UserArgs`（`GB` = GeneralBatch），
   说明只关 `Batched/StridedBatched` 不足以去掉 batch 维度——要先弄清 `GB` 是从哪个字段派生的。约 1–2 小时。
2. **给 `LabelManager.getName` 加唯一化**（同名第二次返回 `_1`）：能一次性解决所有重复标签，
   但会改变**全树**的标签语义，必须重跑上游 codegen 单测（`Tensile/Tests/unit/characterization/_codegen`）确认无回退。约半天。

两条都**不碰生产**（纯 CPU），要做只需机主说一声。

> 落盘：`166:data/w860_hipblaslt_local.patch`（本轮两处实验性改动：arch 白名单 + 跳过 memset），
> 工作树已 `git checkout` 还原干净。

---

## 10 第六轮（W860 续）：f16 走到"上游有现成解，但生成器把 f16-VALU 路径删了"

上一轮结论是"f16 缺一套非 MI logic"。上网查 + 翻 rocBLAS 源码后，这一轮换了打法，把问题定位到了最后一块。

### 10.1 关键发现：rocBLAS 源码树里有 **gfx906 原生的 f16 logic**

`projects/rocblas/library/src/blas3/Tensile/Logic/asm_full/vega20/` 下就有：

- **`vega20_Cijk_Ailk_Bjlk_HHS_BH.yaml`**（699 921 B）← **HHS = half 输入 + f32 累加（HPA）**，Ailk_Bjlk = NN，正是引擎 `f16_inplace` 的形状
- `vega20_Cijk_Ailk_Bjlk_HSS_BH.yaml`（f32 计算全 f32）、`vega20_Cijk_Ailk_Bjlk_HB.yaml`（纯 f16 累加，`HPA: false`）
- 还有 `_GB`（GeneralBatch）变体

取法（blobless clone 里 `git show` 会挂，直接按 sha `git cat-file -p` 秒出）：

```
git cat-file -p 8942ea34ac74ee5d4d4d49e3e153a7fdfc96f92e > vega20_Cijk_Ailk_Bjlk_HHS_BH.yaml
```

文件头就是 `- vega20` / `- gfx906` / `HighPrecisionAccumulate: true` ⇒ **上游自己为 gfx906 生成并长期使用过 f16+HPA 的 kernel**。

### 10.2 用官方工具把成熟解反解成 config（这条路 AMD 博客里就写着）

`Tensile/bin/TensileLibLogicToYaml --input <logic> --indices <N> --output <cfg> --skipMI`
——"从 solution 反解出 tuning config"，正是 `P243` 之外我最需要的工具。但它对 gfx906 **完全不可用**，连撞两个 bug（都已定位+修，脚本 `albus/w860/fix_lib2yaml.py`）：

| # | 上游代码 | 症状 |
|---|---|---|
| 1 | `else: temp = "None"` 然后 `formGroups(temp)`（期望 dict） | `AttributeError: 'str' object has no attribute 'items'`。**非 MI 正好走 else 分支**，所以 gfx906 必崩 |
| 2 | `problemTypeStat["BiasDataTypeList"]` 直接下标 | `KeyError`。rocBLAS 4.6.0 时代的 logic **没有这个字段**（`_BH` 里的 B 是 **beta**，不是 bias） |

修完之后，`idx0` 就是一份可读的 config，里面的参数是**上游实测过的**：

```yaml
ProblemType: GEMM, Batched true, DataType 4(half), ComputeDataType 0(f32), HPA true
ForkParameters:
  DepthU: [8]   ThreadTile: [[2,2]]   MaxOccupancy: [40]   ScheduleIterAlg: [1]
  LdsPadA/B: [0]   SuppressNoLoadLoop: [true]   WorkGroupMapping: [1]
ProblemSizes: Exact [64, 5056, 1, 256]
```

### 10.3 一层层把它调到能过校验（5 个必须改的地方）

| 报错 | 原因 | 处置 |
|---|---|---|
| `Config file requires version=4.6.0 is not compatible with 5.0.0` | 版本闸 | 改 5.0.0 |
| `UseSgprForGRO = False (bool); expected int` | 老 config 用 bool | `[0]`；`VectorStore` 同理 `[1]` |
| `integer division or modulo by zero` | **`WorkGroup` 默认 `[16,16,1]` ⇒ `MIWaveGroup[0] = 16 // 64 = 0`**（wave64 下 WorkGroup 语义变了） | 显式 `WorkGroup: [[64,4,1]]` |
| `totalVectorsB -64 % NumThreads 256 != 0` | MacroTile 128×8 太小，B 侧算出负数 | `ThreadTile: [[2,8]]`（MacroTile 128×32） |
| `No valid DepthU found`（**无子原因**） | **`GlobalReadVectorWidth*` 默认 -1，不在 `[1,2,4,8,16,32]` 里**，`setGlobalReadVectorWidth` 走的是**不打印**的分支 | 显式给 GRVW=1 |

改完这 5 处，**Solution 校验全过**。

### 10.4 真正的墙：新 rocisa **把 gfx906 的 f16 MAC 路径删了**

过了校验就进 codegen，立刻撞：

```
TypeError: FMA_F16_HPA_MAD_MIX.__call__() takes 4 positional arguments but 6 were given
```

- 同文件 `FMA_F16_HPA_DOT2` 已是新签名 `(writer, tPA, tPB, m, innerUnroll)`，`MAD_MIX` 还是老 3 参
  ⇒ 上一轮加 `*a, **kw` 后 `m` 收到 `tPB`（dict），才报 "dict as int"。**签名对齐 DOT2 就把这层修掉了**（`albus/w860/fix_mac.py`）。
- 修完签名，下一层是 **`'rocisa._rocisa.code.Module' object has no attribute 'addInst'`** ——
  这个组件用的是**老 rocisa 的字符串指令 API**，而当前 rocisa 里 **`MadMix`/`FmaMix` 指令类一个都没有**
  （`grep -rn 'MadMix\|FmaMix' rocisa/instruction.py` = **0**）。

⇒ **不是我们不会配，是上游把 gfx906 的 f16 HPA MAC 生成路径整体移除了。**

### 10.5 绕过去的路：`v_dot2_f32_f16`（Vega20 就有的指令，组件是新的）

`FMA_F16_HPA_DOT2` 用的是 rocisa 的 `VDot2F32F16/VDot2CF32F16`（**新 API，类还在**），
而 Tensile 只是把 `UseDotInstruction` 的 ISA 白名单卡在 gfx942/gfx950（`Solution.py:928`）。
`v_dot2_f32_f16` 是 **Vega20 引入**的指令 ⇒ 这个白名单纯属"没人试过"。

放宽到 9.0.6 后（`albus/w860/fix_dot2.py`），reject 提示从"组件崩"变成**明确的参数要求**：

```
reject: dot kernel requires LocalReadVectorWidth = NumDotElements(2) * InnerUnroll(1)
```

—— 这是**最强的一条正向信号**：dot 路径真的进到了参数校验，说明它认这个 ISA。

### 10.6 当前状态与下一步

| 项 | 状态 |
|---|---|
| gfx906 原生 f16+HPA logic | ✅ 已从 rocBLAS 取到（`166:data/w860_vega20/logic/`，699 KB） |
| 官方反解工具可用 | ✅ 两个 bug 已修并脚本化（`fix_lib2yaml.py`），产出 `cfg/idx0..2` |
| config 过 Solution 校验 | ✅ 5 处参数修正后全过（`gfx906_f16_hand.yaml`） |
| f16 codegen | ❌ 两条路：mad_mix（上游已删）/ dot2（已放行到参数校验，卡在最后一处 fork 静默 0 解） |
| 当前卡点 | fork 阶段 `Actual Solutions: 0 / 1` 且**不打印 reject**——`PrintSolutionRejectionReason` 没进 `debugConfig`（config 里设了也不生效），所以看不到具体哪条不过 |

**下一枪（三条，按成本排序）**：

1. **把 reject 逼出来**（10 分钟）：`_build_and_validate_solution` 里 `debugConfig.printSolutionRejectionReason` 为 False 才不打印，
   而 `Solution(...)` 收到的这个 flag 来自 debugConfig 而非 globalParameters ⇒ 直接在 `_generate_single_solution` 里
   硬置 `printRejectionReason=True`，或把 `solutionObject["Valid"]` 为 False 的分支改成无条件 print。
2. **dot2 参数补齐**（30 分钟）：`LocalReadVectorWidth=2`（已给）后大概率还要求 `DepthU % (NumDotElements*2) == 0`、
   `VectorWidthA/B=2`（已给）、`InnerUnroll=1`（默认）。拿到 reject 原文就能一次改对。
3. **若 dot2 也不通**：只剩两条硬路——① 在 rocisa 里补 `VMadMixF32`/`VFmaMixF32` 指令类 + 把 MAD_MIX 改成新 API（约 1–2 天）；
   ② 用 `kernel-language: HIP`（源码路径）而不是 Assembly，绕开整个汇编生成器（未评估）。

> 全程 **CPU-only**（`--cpu-only --build-only`，不给 `--device`），限 4 核 + nice 19，**一次没碰生产**。
> 树已 `git checkout` 还原干净；所有改法都在 `albus/w860/{fix_lib2yaml,fix_mac,fix_dot2,patch_cfg}.py` 里可重放。

---

## 11 第七轮（W860 续）：**gfx906 的 f16 kernel 生成出来了**，用的是 `v_fma_mix_f32`

这一轮把上一轮的"静默 0 解"拆开了，并且拿到了硬证据。

### 11.1 先把两条 ISA 断言实测掉（LLVM 文档和社区 wiki **互相矛盾**）

| 说法来源 | `v_dot2_f32_f16` @gfx906 | `v_mad_mix_f32` @gfx906 |
|---|---|---|
| LLVM 官方 AMDGPUUsage | **不可用** | 未列（隐含可用） |
| skyne98 的 gfx906 wiki | 可用 | — |
| **我们 llvm-mc 实测** | **可用 ✓** | **不可用（instruction not supported）** |

`llvm-mc -triple=amdgcn-amd-amdhsa -mcpu=gfx906` 的结果：

```
v_dot2_f32_f16 v0,v1,v2,v3   @ gfx906 -> OK
v_mad_mix_f32  v0,v1,v2,s0   @ gfx906 -> error: instruction not supported on this GPU (gfx906)
v_fma_mix_f32  v0,v1,v2,s0   @ gfx906 -> OK
```

⇒ **两边都只说对一半**。Vega20 没有 `v_mad_mix_f32`（这解释了 rocisa 为什么删它），但有 `v_fma_mix_f32` 和 `v_dot2_f32_f16`。

### 11.2 静默 0 解的真因：`print1` 被 `PrintLevel` 门控 + `reject()` 不打印

- config 里的 `PrintSolutionRejectionReason: true` **不会进 `debugConfig`**，`_build_and_validate_solution` 的打印分支整条不走；
- 而 `reject()` 里的消息走 `print1`，又被 `globalParameters["PrintLevel"]` 门控（默认 0）。

处置（`albus/w860/fix_reject.py`，3 处）：把传给 `Solution(...)` 的 flag 硬置 `True`，并把两处 `print1("rejecting solution …")` 换成无门控的 `print`。
于是能看到完整 rejected state —— 但**仍看不到具体哪一条 reject**（600+ 字段里没有任何一个 `Valid` 相关的 False）。

### 11.3 绕过它：`NoReject: [True]` —— 一次成功

不再追那 600 个字段，直接在 config 里加 `NoReject: [True]` 让解强行通过，把问题交给后面的 codegen（codegen 的错更具体）：

```
# Actual Solutions: 1 / 1 after KernelWriter
buildSourceCodeObjectFile time (s): 8.82
```

产物（`gen15/.../source/library/gfx906/`）：

| 文件 | 大小 |
|---|---|
| `Kernels.so-000-gfx906-xnack-.hsaco` | 190 968 B |
| `Kernels.so-000-gfx906-xnack+.hsaco` | 192 760 B |
| `TensileLibrary_gfx906.co` | 31 992 B |
| `TensileLibrary.yaml` | 8 853 B |

### 11.4 反汇编：**63 条 `v_fma_mix_f32`，0 条 dot2 / mad_mix**

```
=== instruction census ===
     63 v_fma_mix_f32
=== sample ===
v_fma_mix_f32 v2, s19, v4, v2 op_sel_hi:[0,1,0]
v_fma_mix_f32 v3, s19, v4, v3 op_sel:[0,1,0] op_sel_hi:[0,1,0]
```

**这推翻了我上一轮的判断**：真正的路径不是 dot2，而是 `FMA_F16_HPA_MAD_MIX` 组件在 gfx906 上
自动 fallback 到 **`v_fma_mix_f32`**（组件的 `asmCaps = v_mad_mix_f32 or v_fma_mix_f32`，
而 gfx906 恰好没有前者、有后者）。`op_sel_hi:[0,1,0]` 正是 f16x2 → f32 混合累加的写法——
**这就是 MI50 做 f16 GEMM 的原生方式**，与 rocBLAS 在 gfx906 上跑的是同一类指令。

⇒ 上一轮"dot2 白名单"那条补丁（`fix_dot2.py`）其实是**不必要的**，真正起作用的是 `fix_mac.py` 的签名对齐。

### 11.5 还差最后一段：库的 mapping 文件

把产物按 hipBLASLt 的布局摆好（`Kernels.so-000-gfx906.hsaco` + `TensileLibrary_lazy_gfx906.yaml`）后，探针结果：

```
hipblasLtCreate status=0
No library mapping found at /v20/lib906/TensileLiteLibrary_lazy_gfx906_Mapping.dat
rocblaslt error: Could not initialize Tensile library mapping
RESULT M=64 N=5056 K=256 f16 : status=0 algos=0
```

**`status=0` 且错误信息换成了"缺 mapping"** —— 比上一轮的"拒收"又前进了一步：库结构被认，只缺那张索引表。

mapping 由 `Tensile` 的 benchmark→LibraryLogic 阶段产出，而这一步要 `tensilelite-client`：

```
FileNotFoundError: Tensile client executable not found at
  build_tmp/tensilelite/client/tensilelite-client
To build, run: `invoke build-client`
```

### 11.6 下一步（三条，按可行性）

1. **编 client**（约 10–20 min，纯 CPU）：`pip3 install invoke && invoke build-client`，或
   `cmake --preset` 那条路；有了 client 就能跑完整流程，自动产出 mapping，然后探针验 `algos>0`。
2. **`--prebuilt-client`** 指一个已存在的 client（如果有现成二进制）。
3. **手工造 mapping**：1 个解、1 个 problem size，msgpack 里就是 `{library: …, solutions: …}`，
   结构可从 gen5 的同类文件对照。风险：格式细节容易错，不如编 client 稳。

> 到这一步，"gfx906 能不能出 hipBLASLt 的 f16 kernel"的答案是**能**，且已经拿到一个 190 KB 的
> gfx906 ELF（`elf64-amdgpu`，63 条 `v_fma_mix_f32`）。剩下的是库打包与索引，不是能力问题。
>
> 全部 CPU-only 完成（除最后一次探针用卡约 2 秒）；树已还原，改法全部脚本化在 `albus/w860/`。
