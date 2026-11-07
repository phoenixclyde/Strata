# W839 · gfx906 架构入口：从「有表」到「真的跑」

> 本轮只做一件事：让 `arch_defaults` 那张 gfx906 表**真的被引擎调用**，并把生产从 14 个手工 env 收到 6 个。
> 所有源码改动在分支 `gfx906/0.2.8-mi50` 上完成（P223/P225 的规矩），构建树只做同步。
> 时间：2026-10-31 16:29–17:10（GMT+8）

---

## 1 结论（一句话）

上一轮（W837）"给 gfx906 加了入口"只是**加了一张表**；这一轮查明：**那张表从来没有被任何编译单元引用**，
`arch_defaults.cpp` 被链接器整个丢掉——**入口是死的**。补上调用点后，生产日志第一次打出 gfx906 横幅，
且 `STRATA_GFX906_TUNED=1` 一条 env 复现原先 9 条手工 env 的全部效果（实测差 ≤1.2%，噪声内）。

---

## 2 证据链：它为什么是死代码

| # | 检查 | 结果 |
|---|---|---|
| 1 | `nm -C build-028r/strata \| grep apply_arch_defaults` | **0 个符号** |
| 2 | `grep -a -c 'MI50-class' build-028r/strata`（W837 后的二进制） | **0**（表里的横幅字符串都不在） |
| 3 | `nm -C CMakeFiles/strata.dir/src/program/generate.cpp.o \| grep apply_arch_defaults` | **0 处引用** ⇒ 调用被预处理掉了 |
| 4 | `generate.cpp` 的编译宏（build.ninja DEFINES） | `-DSTRATA_HIP_GFX906=1`、`-D__HIP_PLATFORM_AMD__=1`，**没有 `-DSTRATA_USE_HIP`** |
| 5 | 全 build.ninja 里 `-DSTRATA_USE_HIP` 出现次数 | **1 次**，就是 W776 给 `dflash2.cpp` 单独加的那一处 |
| 6 | 调用点位置 | `generate.cpp:3355`，在 `#if defined(STRATA_USE_HIP)` 块内 ⇒ **永不编译** |

所以链条是：**gfx906 构建不定义 `STRATA_USE_HIP` → 那个块不进编译 → `apply_arch_defaults` 无引用 →
`arch_defaults.cpp.o` 不被从静态库取出 → 整张表（gfx1151/gfx12/gfx906 全部）在引擎里不存在。**

> 顺带纠正一个可能的误读：`arch_defaults.cpp` 在 `CMakeLists.txt:698` 的源文件列表里，**"在构建列表里"
> 不等于"在二进制里"**——静态库成员只在被引用时才被拉入。

### 为什么不能简单全局开 `STRATA_USE_HIP`

`CMakeLists.txt:702-707` 是我们自己 W717 时期留下的注释：

```
[W776 local] gfx906 (STRATA_HIP_GFX906) does not define STRATA_USE_HIP, but dflash2.cpp keys its
CUDA-vs-HIP branches on it ... a global STRATA_USE_HIP would switch CUDA-only paths elsewhere
(W717/P23 measured that).
```

即：全局开会同时切换 38 个条件块的行为，**已实测有副作用**。所以本轮**只加一个针对 gfx906 的调用点**。

---

## 3 改法（分支上的第 9 个 commit；trace 是第 10 个）

`1309b1d` — `src/program/generate.cpp`，+23 行，紧跟原有的 `#if defined(STRATA_HIP_GFX906)`（#1728 wave32 检查）之前：

- 查询 device 0 属性，算 `all_igpu`（与 CUDA 块同一套"所有可见卡同架构"判据；MI50 是独显 ⇒ false）
- 调 `strata::core::apply_arch_defaults(ad.gcnArchName, all_igpu)`
- 多一层 `STRATA_W839_TRACE=1` 的探针（打印 device 查询返回码与 arch 名）——这正是把
  "调用没跑" 与 "跑了但没设东西" 分开的那一步，本轮靠它定位
- 用户已设的变量仍然优先（`setenv(..., 0)`），`STRATA_GFX906_DEFAULTS=0` 仍能整表关掉

---

## 4 验证

### 4.1 直接跑二进制（不经 serve 层，最快判据）

```
$ STRATA_GFX906_TUNED=1 STRATA_W839_TRACE=1 strata-0.1.54n3 --serve --pack /nope ...
strata: [W839] device probe rc=0 name=gfx906:sramecc+:xnack-
strata: gfx906 (MI50-class): 2 exact speed switches on by default (...): GDN_HEAD GFX906_ATTN_REDUCE12
strata: gfx906 (MI50-class): the rounding-level recipe is on (...): GFX906_ATTN_QUERY_SWIZZLE GDN_PP HC_Q8 SELECT_SIMT ROUTE_TAIL_SKIP MMQ_KQ HIP_PROMPT_F16
```

### 4.2 三臂实测（同镜像 `0.2.8p2`，8×128 tok decode + 3 档 read，中位）

| 臂 | 二进制 | env | decode tok/s | read 1958 | read 3718 | read 6666 |
|---|---|---|---:|---:|---:|---:|
| **A** | n3（含调用点） | **14 条手工** | **51.60** | 4114 ms | 6045 ms | 9703 ms |
| B | n3（**无**调用点，误部署的旧件） | 5 条 | 50.35 | **7144 ms (+74%)** | — | — |
| **B2** | n3（含调用点） | **6 条**（5 + `TUNED=1`） | **51.40** | **4065 ms (−1.2%)** | 6019 ms (−0.4%) | 9704 ms (+0.0%) |

- **B 那臂是意外的对照**：它少 9 条 arch env，prefill 立刻 **+74%**（正是 `MMQ_KQ` / `PROMPT_F16` 的账），
  证明测量对这 9 条 env 极其敏感，也反证 B2 真的吃到了它们。
- **B2 ≈ A**（decode −0.4%，read 三档 −1.2%/−0.4%/+0.0%，全在噪声内）⇒ 入口复现手工 env。

### 4.3 过程里的两次自我更正（都记下来）

1. 第一版 `n3`（16:33 部署）**还没含调用点**，A/B 两臂跑的是它，所以两臂都没有横幅——
   我一度以为"代码在但静默"，加了 trace 才分清是**根本没用新二进制**。
   教训：**部署物与构建产物的 md5 必须当场核对**，本轮已经写进门禁（PROVENANCE + binary 字符串）。
2. `/proc/<pid>/environ` **不能**用来验证 `setenv` 效果：它是 exec 时的初始环境拷贝，
   `setenv` 改的是进程内的 `environ` 数组，不回写该文件。**判据只认横幅/行为**，不认这个文件。

---

## 5 落生产（已执行）

| 项 | 改前 | 改后 |
|---|---|---|
| 引擎 | `strata-0.1.54n2` | **`strata-0.1.54n3`** |
| env 条数 | 14 | **6** |
| env 清单 | 9 条 arch + 5 条非 arch | `HSA_OVERRIDE_GFX_VERSION`、`STRATA_GFX906_TUNED=1`、`STRATA_PREFILL_CPU_SHARE`、`STRATA_PREFILL_CPU_SHARE_MAX`、`STRATA_RESIDENT_HEADROOM_GIB`、`STRATA_ROCBLAS_TUNING` |
| args | 33 | 33（未变） |
| 镜像 | `strata-gfx906:0.2.8p2` | 同（未变） |

就绪后（`/health` ok，约 5 min）：

- 生产日志出现 **2 行 gfx906 横幅**（见 §4.1）
- 显存 **33.5 / 34.3 GB = 97.4%**、**7463 槽 / 21.79 GiB**、提示借用 **1578 槽 / 4.62 GiB**、预热 **12820 MB/s**（与 W835 记的 12739 差 0.6%，属逐次波动，不是「逐项一致」）
  —— 与切换前逐项一致
- 门禁 **17 项全 PASS**

**回滚件**：配置 `data/strata-huihui-ud-iq4_xs.json.bak-w839`；旧二进制 `data/bin/strata-0.1.54n2`（保留）。

---

## 6 顺带盘出的资产：`generate.cpp` 里还有 **28 个** HIP 条件块对 gfx906 不生效

静态清点（`STRATA_USE_HIP` 块共 38 个，其中不含 `STRATA_HIP_GFX906` 的 **28 个**）。对本机有实际意义的：

| 行 | 内容 | 对我们的意义 |
|---|---|---|
| 2111 / 2124 / 2140 / 4948 / 2153 | `decode_defaults_arch_ok()` 判定、`STRATA_PCIE_FRAC_DEFAULT=auto` | **decode 默认档与 `pcie_frac` 自适应**在这套构建里是关的；我们手写 `--pcie-frac 0.20`，所以"auto"这条路**从未被测过** |
| 4208 | `o.pcie_frac_auto = o.layer_split.empty(); o.pcie_probe_gbps = bw` | 同上：单卡自适应分数在 gfx906 构建里不存在 |
| 3713 | 启动时校验"用到的每张卡都有该二进制代码" | 安全网，缺它只是错误信息更晚 |
| 598/… | `STRATA_HIP_ADAPT_KERNEL_COPY`（#884） | 已知的反向优化（会挂），不需要 |

**纪律**：这些**不能一次性打开**（W717/P23 已测出全局开有副作用）。下一步若要动，按"一次只放一块、
每块单独 A/B"的方式加 `|| defined(STRATA_HIP_GFX906)`，与 P222 那条"别的架构的开关一律先单项测"同一规矩。

---

## 7 流程固化：源码只在分支改

```
分支（真相源）  /home/albus/strata166/gfx906      git, gfx906/0.2.8-mi50 @ 1309b1d
构建树          /home/albus/strata166/src028     非 git，由 sync_gfx906.sh 校验/同步
推送仓库        phoenixclyde/Strata               fetch 走代理，push 只走 SSH（上游 remote 已 DISABLE）
```

`sync_gfx906.sh` 本轮补上关键一类：

- **9 个文件**（与上游 v0.2.8 基座相同的补丁文件）：按 md5 比对，不一致才复制
- **1 个锚点补丁器** `patches/apply_w839_generate.py`：`generate.cpp` 在 main 与 v0.2.8 之间被上游改了
  几百行，**不能整文件复制**（会把 main 的引擎塞进 v0.2.8 构建），改为按锚点幂等落我们的 23 行
- `CMakeLists.txt` 仍然只查标记、不复制（同样的理由）

`--check` 输出：9 个 `same` + `applied src/program/generate.cpp` + `drift 0`。

门禁（`verify_patches.sh`）本轮新增 4 项，共 **17 项**：

| 新增 | 判据 |
|---|---|
| W837 tree | `arch_defaults.cpp` 含 `MI50-class` |
| W839 tree | `generate.cpp` 含 `W839 local` |
| **W839 binary** | **部署的引擎二进制里含 `exact speed switches`**（树里有 ≠ 二进制里有，这一条才挡住死代码） |
| PROVENANCE | **默认取生产配置里的 exe**，不再硬编码 `n2`（旧写法会检查一个没人用的文件还报 OK） |

---

## 8 局限

1. **解码/预填性能本身没有变化**：本轮只是把"手工 env"换成"引擎自己设同样的 env"，值逐条相同，
   所以 A 与 B2 在噪声内。真正的收益是**可维护性与可移植性**（换卡/换人不用抄 9 条 env）。
2. `TUNED=1` 涵盖的 7 项里，`QUERY_SWIZZLE` 与 `GDN_PP` **仍未单独做位等价门**（P215 已记），
   所以那是"生产一直在用的配方"，不是"新验证过的配方"。
3. 三臂各 1 次启动、n=8/3，**判不出 1% 级差异**；本轮结论只到"等价"这一档。
4. 28 个死块只做了静态清点，**没有一个被打开过**。
