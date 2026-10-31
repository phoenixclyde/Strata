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
