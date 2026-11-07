## W839（架构入口接线，2026-10-31 16:29–17:10）

- **决定性发现**：W837 的 gfx906 架构入口是**死代码**——`apply_arch_defaults` 只被测试调用，
  `generate.cpp:3355` 的调用点在 `#if defined(STRATA_USE_HIP)` 内，而 gfx906 构建的宏只有
  `-DSTRATA_HIP_GFX906=1`、`-D__HIP_PLATFORM_AMD__=1`；全 build.ninja 仅 1 处 `-DSTRATA_USE_HIP`
  （W776 给 dflash2.cpp）。⇒ `arch_defaults.cpp` 未被任何编译单元引用，**静态库成员不被拉入**，
  nm 无符号、二进制无横幅字符串。**"在 CMake 源文件列表里" ≠ "在二进制里"。**
- **修法**：分支 commit `1309b1d`（+23 行，`STRATA_HIP_GFX906` 下加专属调用，同 CUDA 块 all_igpu 判据，
  `setenv(...,0)` 用户优先），`9ac564f` 加 `STRATA_W839_TRACE=1` 探针（打印 device 查询 rc 与 arch 名）。
  **不全局开 STRATA_USE_HIP**（W717/P23 已测有副作用）。
- **三臂（同镜像 0.2.8p2，8×128 decode + 3 档 read，中位）**：A(n3,14env) 51.60/4114/6045/9703；
  B(无调用点的旧件,5env) 50.35/**7144(+74%)**；B2(n3,6env 含 TUNED) 51.40/4065/6019/9704 ⇒ **B2≈A**。
  B 那臂成了意外对照：少 9 条 arch env，prefill 立刻 +74%。
- **已落生产**：exe `n2`→`n3`，env **14→6**（5 条非架构 + `STRATA_GFX906_TUNED=1`），args 33 不变，镜像不变；
  就绪后生产日志有 **2 行 gfx906 横幅**；显存 33.5/34.3GB(97.4%)、7463 槽/21.79GiB、1578 槽借用、12820MB/s 与切换前一致；
  门禁 **18 项 PASS**。回滚：配置 `.bak-w839` + 旧二进制 `n2`。
- **两条方法教训**（都进登记）：①`/proc/pid/environ` **不反映 setenv**（exec 时快照），验证运行时 env 只能靠横幅/行为；
  ②部署物与构建产物必须**当场核 md5**——首轮 A/B 跑的是未含调用点的旧 n3，导致"有代码无横幅"的假象。
- **新资产 P227**：`generate.cpp` 里 **28 个** `STRATA_USE_HIP` 块对 gfx906 不生效（38 个块中 10 个含 GFX906）。
  有意义的是 `decode_defaults_arch_ok()`、`STRATA_PCIE_FRAC_DEFAULT=auto`、`pcie_frac_auto/pcie_probe_gbps`
  ——**单卡 pcie 自适应这条路我们从来没有过**，生产一直固定 0.20。只能**逐块**加 `|| defined(STRATA_HIP_GFX906)` 并单独 A/B。
- **流程**：源码只在分支改；`sync_gfx906.sh` 现在 = 9 个文件按 md5 + **1 个锚点补丁器**
  （`patches/apply_w839_generate.py`，因为 generate.cpp 在 main 与 v0.2.8 之间差数百行，不能整文件复制）；
  门禁新增 W837/W839 树标记 + **"部署的引擎二进制含 banner 字符串"** + PROVENANCE 默认取生产 exe。
- 登记 **P226（ADOPTED）/P227（PROPOSED）**，224 行；补丁清单 9 行（含 commit）。
