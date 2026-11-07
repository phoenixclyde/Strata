# W836　我们的 gfx906 分支：`gfx906/0.2.8-mi50`

> 目的：把"改了没提交"和"提交了没被接受"的源码改动，**相对上游最新**收进一个分支，在 166 与 GitHub 同时管起来。
> 建立日期 2026-10-31。生产未改动。

---

## 1 分支身份

| 项 | 值 |
|---|---|
| 仓库 | `git@github.com:phoenixclyde/Strata.git`（public） |
| 分支 | **`gfx906/0.2.8-mi50`** |
| head | **`642de24f`**（2026-10-31，**8 个 commit**）—— 快照时点；现 head `9ac564f`、**10 个 commit** |
| **基线** | `c62d5e3a` = 上游 `Niko1221/Strata` main @ 2026-10-31 |
| 相对上游 | **ahead 8 / behind 0** |
| 改动面 | **10 个文件，+216 / −9**（快照时点；AUDIT13 用 GitHub compare 核到现为 **11 文件 / +243 −9**） |
| 166 工作副本 | `/home/albus/strata166/gfx906`（depth-1 clone，5319 文件，已跟到 `642de24`） |
| 166 构建树 | `/home/albus/strata166/src028`（**不是 git 仓库**，由同步脚本校验） |
| PR 链接 | https://github.com/phoenixclyde/Strata/pull/new/gfx906/0.2.8-mi50 |

**基线取的是上游当天最新**，不是 v0.2.8 tag：`v0.2.8` = `870aedd9`（10-29），而 main 在 10-31 已推进到
`c62d5e3a`。**第一次取时还是 `870aedd9`，二十分钟后再取就变了** —— 上游在动，这也是"必须每次现取"的直接证据。

## 2 七个 commit（一个补丁一个，可单独摘出来发 PR）

| # | commit | 文件 | 行数 | 补丁 |
|---|---|---|---:|---|
| 1 | `c5fd0796` | `CMakeLists.txt` | +18/−1 | **W793** gfx906 接 rocBLAS |
| 2 | `01e01636` | `CMakeLists.txt` | +6 | **W776** `STRATA_USE_HIP` 只作用到 `dflash2.cpp` |
| 3 | `b42e4bc0` | `src/kernels/cuda/qsa_decode_attn.cu` | +12/−2 | **W794** query swizzle 覆盖 `k8v4`（kv_mode 3） |
| 4 | `46aaaba5` | `serve/telemetry.py` | +51/−3 | **TEL-PCIE** PCIe 带宽采样 + FRU/显存校验 |
| 5 | `f3d35b86` | `serve/web/app.css` | +6 | **W831** 解除 monitor 页 1920px 封顶 |
| 6 | `7c38cb4e` | `serve/web/app.js` | +3/−1 | **WEB-UI** PCIe `· peak N MB/s` 后缀 |
| 7 | `923c2118` | `include/strata/platform/hip_compat/strata_hip.h` | +4 | **W830-COMPAT** stream priority 两个宏 |
| 8 | `642de24f` | `gfx_arch.hpp` / `arch_defaults.hpp` / `arch_defaults.cpp` / `arch_defaults_test.cpp` | +122/−2 | **gfx906 架构入口**（谓词 + 精确表 + opt-in 配方），见 §10 |

> 第 7 条是这一轮**差点又漏掉**的：`LOCAL_PATCHES.tsv` 里有它，但我第一次建分支时只处理了 5 个文件，
> 是靠"全量对撞分支树 vs 构建树"才捞回来的。

## 3 每个补丁的理由

| 补丁 | 为什么必须 | 证据 |
|---|---|---|
| **W793** | gfx906 分支不走 `cmake/hip_backend.cmake`，`STRATA_ROCBLAS_AVAILABLE` 从未定义 ⇒ `gemm.cu` 整段 rocBLAS 被编掉，`STRATA_ROCBLAS_TUNING` **一直是空转** | 修复前构建日志有 `gemm.hpp:96: warning: private field 'rocblas_state_' is not used`，修复后 0 条；同镜像只差 exe 的 ABBA ×2：TTFT 常数 **1190 → 915 ms（−23%）**，斜率不变 |
| **W776** | gfx906 定义 `STRATA_HIP_GFX906` 但**不定义** `STRATA_USE_HIP`，而 `dflash2.cpp` 用它分支 ⇒ 编的是 CUDA 路径（默认双流 + 高优先级流），与 HIP 分支意图相反 | `build.ninja` 里只有 `dflash2.cpp` 带 `-DSTRATA_USE_HIP=1`，全树仅此一处 |
| **W794** | swizzle 是 **q 侧 LDS 双射**，不碰 KV 载荷，与 KV 格式无关；上游只开给 `kv_mode 1`，把生产的 `k8v4` 留在未 swizzle 路径 | 选路谓词 + 两处 dispatch 同时加 `kv_mode 3`；置换搬整 16 维组 ⇒ 归约求和次序不变，选择逐位相同 |
| **TEL-PCIE** | 引擎自己不上报 host→GPU 流量 | 合并式（非整文件替换），保留上游后来的 `_loop` 健壮性；`py_compile` 通过 |
| **W831** | 上游 v0.2.7.1 把 `.monitor` 从 1240px 改成 `min(100%,1920px)`，2560 宽窗口两侧各空 ~320px | 只作用 `.monitor`；`.about`/`.chat` 保持上游 1100（2560×1080 无头渲染两页验证） |
| **WEB-UI** | 原补丁 78 行增量里 **74 行上游 v0.2.8 已原生实现**，只剩 PCIe 峰值后缀是我们的 | 空载 `peak < 1` 不显示；标记改 `pciePk`（旧的 `saveApiKey` 是**假绿**，上游自带该词） |
| **W830-COMPAT** | 上游 0.1.54 的 `dflash2.cpp` 直接调 `cudaStreamCreateWithPriority` / `cudaDeviceGetStreamPriorityRange`；wave32 HIP 后端靠 hipify 得到它们，gfx906 的手写宏表没有 ⇒ 编不过 | 只加两行 `#define`，紧邻既有 stream 条目 |

## 4 落补丁的方式：不是搬 diff，是让补丁在上游最新树上重新落一遍

| 文件 | 上游自 v0.2.8 的改动 | 落法 |
|---|---:|---|
| `qsa_decode_attn.cu` / `telemetry.py` / `app.css` / `app.js` / `strata_hip.h` | **0 个 commit** | 直接取我们这版内容 |
| `CMakeLists.txt` | **+29/−1（上游在动）** | **重跑幂等补丁脚本**（带锚点断言） |

直接搬 diff 会与上游那 29 行冲突；`restore_cmake.py` 有锚点断言，它报 `applied: ['W793a','W793b','W776']`，
说明三个锚点在上游最新树上都在。

## 5 验证

| 检查 | 结果 |
|---|---|
| 远端分支 | ✅ `gfx906/0.2.8-mi50` @ `923c2118` |
| 相对上游 | ✅ ahead 7 / behind 0 |
| 改动面 | ✅ 6 文件 +94/−7（第 7 个 commit 时点；无多余） |
| 补丁标记 | ✅ `W793`×1 `W776`×1 `W794`×1 `BW_REFRESH_S`×2 `ALBUS-W831`×1 `pciePk`×2 `cudaStreamCreateWithPriority`×1 |
| `py_compile` | ✅ `serve/telemetry.py` OK |
| **W793 在上游最新树上生效** | ✅ configure 输出出现 `/opt/rocm/lib/cmake/rocblas/rocblas-config.cmake:90 (find_dependency)`，即 `find_package(rocblas)` 已被执行并找到包。（AUDIT13 更正：`find_package` 执行 **≠** `STRATA_ROCBLAS_AVAILABLE` 进了编译单元，更 ≠ 链接进二进制；同一张表下一行还写着「完整编译未做」。真判据是构建日志里 `rocblas_state_ not used` 归零 + 二进制里 `rocblas` 字符串数。） |
| 完整 configure（到 `build.ninja`） | ⚠️ 未完成。三次后台 configure 都卡在 `_deps` 的 `FetchContent` 编译（并发抢资源），已清掉；目录留在 `gfx906-build*`（root 所有，可删） |
| 完整编译 | 未做（约 40 min）。**但生产 `strata-0.1.54n2` 就是由同一套补丁的 `src028` 构建的**，不是本分支 |

**诚实结论**：分支的**内容**已验证（7 个补丁齐全、锚点在上游最新树上成立、rocBLAS 探测已触发）；
分支的**端到端构建**未验证，原因是上游 `_deps` 拉取慢，与我们的补丁无关。

## 6 同步脚本与其边界（重要）

`/home/albus/strata166/tmp/sync_gfx906.sh`：`--check` 只报漂移，不带参数则同步 + 跑补丁门禁。

**但它不能整文件覆盖 `CMakeLists.txt`**：分支的 CMakeLists = 上游 main + 补丁，src028 的 = 上游 v0.2.8 + 补丁，
两边基底不同（上游走了 29 行）。当前实测就是这 6 个文件里 5 个 `same`、`CMakeLists.txt` `DIFF`。

正确用法：
- 对**上游未改**的 5 个文件：可以字节比较/同步；
- 对 `CMakeLists.txt`：**只比较补丁标记**（`W793`/`W776` 是否存在），不比 md5。
- 若要让构建树跟上上游最新，那是**升级动作**（重跑 `restore_cmake.py` + 门禁 + 重建），不是同步动作。

## 7 日常怎么用

```bash
# 改代码：在分支里改、提交、推
cd /home/albus/strata166/gfx906
git checkout gfx906/0.2.8-mi50
$EDITOR src/kernels/cuda/qsa_decode_attn.cu
git commit -am "gfx906: ..." && git push origin gfx906/0.2.8-mi50

# 检查构建树相对分支有没有漂移（只读）
bash /home/albus/strata166/tmp/sync_gfx906.sh --check
```

**核心变化**：以前补丁只存在于 `src028` 的文件系统里（`src028` 根本不是 git 仓库），丢了无法追溯
（W830 那次就是这么丢的）。现在**源码真相源是分支**，`src028` 只是构建树。

## 8 与第三方 PR 的关系

| PR | 作者 | 关系 |
|---|---|---|
| `#3986` `gfx906: fix the build of src/core/dflash2.cpp` | **MarcoTool** | 与 **W776** 同一件事 |
| `#4766` `gfx906: build dflash2 for Radeon VII` | **nfriedly** | 同上 |

两者都不是我们提的，且都还 open。我们的 W776 **做法不同**（只给该文件加宏，不全局开 `STRATA_USE_HIP`），
可以作为第三种方案提交，并在正文引用这两条说明差异。

## 9 这一轮踩到并修掉的两个方法错误（写下来免得重犯）

1. **`git diff <tag> <branch> -- <file>` 在 shallow 仓库里会静默返回空**。我据此判"上游没改过这个文件"，
   于是把 68 个"上游前进"的文件误判成"我们的补丁"。正确做法：**不依赖历史，直接比 blob 内容**。
2. **判据失效时数字会显得很"干净"**（residue=0 / ours=68 这种整齐结果），反而更容易被当真。
   ⇒ 任何"全量分类"的结果，先用 2–3 个**已知不可能属于某类**的样本做反证（比如 `src/dsv41/*` 我们从未碰过）。

---

> **W839 更正（2026-10-31）**：本节写的「入口」当时只是**加了一张表**，表本身没有被任何编译单元引用 ——
> apply_arch_defaults 的调用点在 `#if defined(STRATA_USE_HIP)` 块内，而 gfx906 构建只定义 STRATA_HIP_GFX906，
> 于是 arch_defaults.cpp 被链接器整块丢掉（nm 无符号、二进制无横幅字符串）。本节「重编后行为应不变」
> 因此是对的，但理由不完整：**不变是因为表根本没跑**。调用点由 W839 补上（commit 1309b1d，trace 为 9ac564f），
> 详见 W839_ARCH_ENTRY.md。

## 10 第 8 个 commit：给 gfx906 一个架构入口

### 10.1 改之前的状态

`arch_default_env()` 在 `if (!gfx_arch_is_gfx1151) return t;` 处返回空表，`gfx_arch.hpp` 只有 4 个谓词
（gfx11_wmma / gfx12 / gfx12_wmma / gfx1151），**没有 gfx906**。gfx906 只在各 kernel 里靠字符串认身份。

后果最直接的是这两个开关——**它们是为 gfx906 写的，却默认关闭**：

| 开关 | 读取点 | unset 时 |
|---|---|---|
| `STRATA_GFX906_ATTN_REDUCE12` | `qsa_decode_attn.cu:997` | **off** |
| `STRATA_GFX906_ATTN_QUERY_SWIZZLE` | `qsa_decode_attn.cu:967` | **off** |

也就是说：不知道这两个名字的 gfx906 用户，两个专用 kernel 一个都用不上。

### 10.2 改了什么（按上游的既有规矩分两层）

上游 `arch_defaults.hpp` 的原则写得很明确：**表里默认开的必须实测且位等价；改 bit 的保持 opt-in**。
所以没有把生产的 14 个 env 一股脑塞进去，而是照 gfx1151 的做法分两层：

**① 精确表 `arch_default_env("gfx906")` —— 2 项，都有位等价实测**

| 开关 | 位等价证据 |
|---|---|
| `STRATA_GDN_HEAD=1` | teacher-forced LOGPOS：KL mean **0.0000**、median 0、argmax **100%**、top-10 **1.00**、mean\|Δlp\| **0.00000** |
| `STRATA_GFX906_ATTN_REDUCE12=1` | 同一批 prompt 的三份 LOGPOS dump **md5 完全相同**（开关开/关/再开） |

关掉：`STRATA_GFX906_DEFAULTS=0`；`STRATA_DEFAULTS=026` 时返回空（0.2.6 没有 gfx906 表可还原）。

**② opt-in 配方 `gfx906_tuned_env()` —— 7 项，`STRATA_GFX906_TUNED=1`**

| 开关 | 值 | 位代价（同引擎 teacher-forced） |
|---|---|---|
| `STRATA_GFX906_ATTN_QUERY_SWIZZLE` | 1 | 未做 md5 门（生产在用） |
| `STRATA_GDN_PP` | 2 | 未单独门（gfx1151 表第二项） |
| `STRATA_HC_Q8` | 1 | KL 0.0011，argmax 100% |
| `STRATA_SELECT_SIMT` | 1 | KL 0.0004，argmax 100% |
| `STRATA_ROUTE_TAIL_SKIP` | 7 | KL 0.0008，argmax 100% |
| `STRATA_MMQ_KQ` | 1 | KL 0.0171，argmax 100%，**+68% prompt** |
| `STRATA_HIP_PROMPT_F16` | 1 | KL 0.0026，约 1.6× prompt |

**注释里明写"这些 KL 不相加"**：五项同关的总量 0.0293，而逐项和只有 0.0062（P215）。

**③ `gfx_arch_is_gfx906()`** 谓词，与前四个并列。

### 10.3 验证（不用等 40 分钟全量构建）

`arch_defaults_test` 只链接 `arch_defaults.cpp`，可以单独编译：

```
g++ -std=c++17 -I include -o /tmp/adt src/core/arch_defaults_test.cpp src/core/arch_defaults.cpp
```

| 检查 | 结果 |
|---|---|
| 编译 | ✅ rc=0 |
| 原有用例（gfx1151 18 项 / gfx12 9 项 / igpu 集） | ✅ 全部仍然通过 —— **没有改动任何现有架构的行为** |
| gfx906 新用例 | ✅ 表恰好 2 项、精确表里"不含任何改 bit 的开关"、`defaults026` 返回空、`DEFAULTS=0` 返回空、tuned 仅 gfx906 且需 `TUNED=1`、`gfx9060` 不误匹配、`gfx906:sramecc-:xnack-` 后缀可用 |
| 运行时 banner（**来自单独编译的测试件，不是引擎**） | ✅ `strata: gfx906 (MI50-class): 2 exact speed switches on by default (STRATA_GFX906_DEFAULTS=0 turns them off; a switch you set is kept): GDN_HEAD GFX906_ATTN_REDUCE12` |
| 用户设置优先 | ✅ 预先设 `GDN_HEAD=0` 后再 apply，`set 0` 且值保持 0 |

### 10.4 已同步到构建树，但**还没重编**

`sync_gfx906.sh` 已把这 4 个文件同步进 `src028`，**补丁门禁 11 项全 OK**（当时项数；AUDIT13 时已扩到 17 项）。
生产二进制仍是 `strata-0.1.54n2`（不含本改动）；下次重编才会生效。

**重编后行为应当完全不变**：生产启动脚本已经手工设了这 9 项（2 + 7），而 `apply_arch_defaults` 只设
"用户没设过的"变量 ⇒ 两边取值一致，不产生新的差异。

### 10.5 同步脚本的一处必要修正

原来 `FILES` 里含 `CMakeLists.txt`，会**整文件覆盖**——那会把上游 main 的 29 行改动拖进 `src028`（v0.2.8 基底）。
已改为：**CMakeLists 只检查补丁标记（`W793` / `W776 local`），不做文件复制**。
