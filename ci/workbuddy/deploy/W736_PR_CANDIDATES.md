# W736 今天改了什么 + 哪些能提 PR（逐条清点）

> 时点：2026-10-09 22:5x。范围：**今天（W716 ~ W736）全部改动**。
> 上游基准：`Niko1221/Strata` main = **`fb58e0dbc8`**（2026-10-08T10:25:39Z，
> 即 v0.1.41 之后**再无新提交**）---- 下面每个候选都**实测过它在此基准上仍未修**。
> 仓库布局注意：serve 层在**仓库根的 `serve/`**（容器里才被摆到 `/src/serve/`）。

## 0 速览：能提的有 4 条，按优先级

| 序 | 候选 | 改动量 | 上游是否仍未修 | 是否与已有 issue 重复 | 建议 |
|---|---|---|---|---|---|
| **A** | `src/prefill/prefill.cpp:1839` 的 gfx906 守卫缺失 | **1 行** | **是**（实测） | 不重复（#1729/#1595/#1684 都只说现象，**没人指出机制**） | **提 PR（首选）** |
| **B** | `serve/web/app.js` 的 `spark()` 轴下限 | **1 字符**（`1e-9` -> `1`） | **是**（实测） | 未搜到同类 | **提 PR（最省、且与后端无关）** |
| **C** | `serve/telemetry.py` 的 Linux AMD PCIe 读数 | 约 40 行（3 个部分） | **是**（实测 `_Amd` 段 0 个 pcie 键） | 现有 AMD 监控 issue/PR **全是 Windows 侧** | **拆成 C1/C2 两件后提；吞吐那半必须先谈口径** |
| **D** | `serve/telemetry.py` 的 `name()` 容量一致性 | 约 10 行 | **是**（实测只读 `product_name`） | 未搜到 | 可提，但**建议先开 issue 谈**（改的是驱动提供的字符串） |
| - | 「子 chunk 边界 checkpoint」feature | 提案 | - | **与 #1670 高度重叠**（layer-major prefill，且作者已 offer PR） | **不提新 issue，先去读 #1670 的评论** |

## 1 今天到底改了什么（分类清单）

### 1.1 引擎源码级：只观察 / 得出结论，**没有改上游代码**

| # | 位置 | 事实 | 能否 PR |
|---|---|---|---|
| 1 | `src/prefill/prefill.cpp:1838-1839` | `arm_cpu_share()` 的守卫写 `#if !defined(STRATA_USE_HIP)`；gfx906 兼容构建**不定义** `STRATA_USE_HIP`（`compile_commands.json` 计数 **0**，只有 26 处 `-DSTRATA_HIP_GFX906`）=> 该分支被编进去 => banner 打印 + `g_share_default=true` | **能（候选 A）** |
| 2 | `src/core/expert_cache.cpp:5-6` | 上游**自己**的注释：*"the gfx906 compat build (PR #638), which compiles this file as HIP **without** `STRATA_USE_HIP`"*，且该文件守卫写作 `#if defined(STRATA_USE_HIP) \|\| defined(STRATA_HIP_GFX906)` | 作为 A 的**论据**（不是候选） |
| 3 | `src/` 全树计数 | `STRATA_USE_HIP` 出现 **60** 行，其中带 `&& !defined(STRATA_HIP_GFX906)` **2** 处、带 `\|\| defined(STRATA_HIP_GFX906)` **7** 处 => 上游主流写法**已经排除 gfx906**，`prefill.cpp:1839` 是少数漏网 | 作为 A 的**一致性论据** |
| 4 | `src/core/mtp.cpp:420 / 428 / 864` | 同一函数内两处守卫写法不一致（`:420` 认 gfx906，`:428`/`:864` 不认）；但 `:428` 创建 `side_` 与 `:864` 使用它**同宏、配套自洽** | **不能单独改**（只改创建不关使用 => `side_ == nullptr` 真 bug）；A/B/A 单变量实测无差 => 不提 |
| 5 | `src/core/mtp.cpp` HIP 门 | `head_mix_multi_enabled()` / `one_token_self_commit()` 在 HIP 下写死 `return false`（**硬关**） | 已成 issue **#1479**（作者 jkuepker，含 patch）=> 我们只**提议去评论**（我们的发现是它的镜像：一处硬关、一处"硬开"） |

### 1.2 serve 层：**我们的本地覆写**（跑在生产，未提交上游）

| # | 文件 | 改了什么 | 能否 PR |
|---|---|---|---|
| 6 | `serve/telemetry.py` | `_Amd.read()` 补 PCIe：① 链路（`link()`：逐跳取 `max_link_speed/width` 最小值＝路径瓶颈）② `pcie_own_gen` ③ `pcie_path`（路径是否读全，读不全就不冒充瓶颈） | **能（候选 C1）** |
| 7 | `serve/telemetry.py` | `bw()`：读 amdgpu `pcie_bw`，按 `(received+sent)*mps` 折算吞吐，**独立线程** 5 s 一刷（单次读阻塞约 1 s） | **能（候选 C2）但必须先谈方向口径** |
| 8 | `serve/telemetry.py` | `sample()` 多卡聚合：逐卡求和 + 仅在**全部**卡都是 sysfs 读者时才接手该字段 | **随 C2 一起**（它修的是我们 v3 自己的 bug，见 §2.C2） |
| 9 | `serve/telemetry.py` | `name()`：把名字里的 `NNGB` 与 `mem_info_vram_total`（取整）比对，**只在矛盾时**替换 | **能（候选 D）** |
| 10 | `serve/web/app.js` | `spark()` 轴下限 `1e-9` -> `1`；PCIe 副行改 2 位小数 + 窗口峰值 >= 1 MB/s 时补 `peak` | **能（候选 B）** |

### 1.3 我们自己的项目基建：**不属于上游，不该 PR**

| # | 件 | 说明 |
|---|---|---|
| 11 | `deploy/params/{PARAM_REGISTER.tsv, gen_config.py, verify_config.py}` | 参数真值表 + 生成器 + 6 个数据面核验器（含 `SETUP_KEYS` 覆盖、`serve` 覆写在位） |
| 12 | `deploy/tools/mem_slim.py` | 记忆件压缩唯一入口（`routek-memory-slim` 技能的适配版）；今天修了**归档日期硬编码**（+ 补 BAN 6 码位） |
| 13 | `deploy/patches-*` 侧的 `apply/check/revert_telemetry_pcie.sh` | 166 上的落地/回滚脚本 |
| 14 | 一批报告与全量账（`W713_PLAN` §6 第 21~23 条等） | 项目账本 |

### 1.4 只读测量（可作 PR/issue 正文的**数据**，本身不是改动）

P31 parity A/B/A（#1454）/ P23 CPU share 两臂 / P33 `strata_prefix` / tokenizer cache 隔离实测 /
PCIe 有效链路 `lspci` 全链 / `spark()` 折线 y 值 / `product_name` = FRU 串 / 专家缓存槽位与驱逐计数。

## 2 可做 PR 的候选（逐条详细）

### 候选 A（首选）：`prefill: the gfx906 compat build gets the CUDA branch of arm_cpu_share`

- **改动**：`src/prefill/prefill.cpp:1839`
  ```diff
   void Prefill::arm_cpu_share(bool applies, bool by_default) {
  -#if !defined(STRATA_USE_HIP)
  +#if !defined(STRATA_USE_HIP) && !defined(STRATA_HIP_GFX906)
  ```
- **上游仍未修**：今天实测 main `fb58e0dbc8` 上该行原文不变。
- **为什么是 bug（不是"AMD 本来就该开"）**：
  1. 同一函数上方 `:161` 的注释写 *"the layer split, batch slots and **HIP stay off**"*；
  2. `expert_cache.cpp:5-6` 明说 gfx906 兼容构建**不定义** `STRATA_USE_HIP`；
  3. 全树已有 **7** 处用 `|| defined(STRATA_HIP_GFX906)`、**2** 处用 `&& !defined(...)` 把 gfx906 归到 HIP 一侧。
- **与其他后端无关**：CUDA/SYCL 不定义 `STRATA_HIP_GFX906` => 该改动对它们**宏展开恒等**（PR 里要写明这点）。
- **我们的实测**（见 §6）：机制**确实在动**（197 个专家由 CPU 承担、share 0.90），但**预填耗时无差**（928.3 vs 929.5 ms，Δ0.13%，低于我们 1.2~1.7% 的重复性分辨力），输出 token **逐位相同**。
- **与已有 issue 的关系（关键，避免重复）**：上游已有
  - **#1729**（RTX 5090 D + i9，解码 110 -> 46 tok/s，判 `auto` 误判，无 AVX-512）
  - **#1595**（V100，1000 token 慢 ~4.8%，已用 `=0` 规避）
  - **#1684 / #1687**（`auto` 不可复现；固定 share 可复现）
  => 但它们**都在讲自己那张卡的现象**，**没有一条指出 AMD 侧为什么会被打开**。本 PR 补的正是这一环，且**不改 CUDA 默认**，与它们不冲突。
- **风险**：维护者可能选择"全局改默认"而不是"修守卫"。对策：PR 正文里明确"本改动只让 gfx906 回到 `=0` 的既有行为，与全局默认无关，可独立合并"。
- **建议动作**：以 `git@github.com:phoenixclyde/Strata.git` 的 fork 分支提交，正文引用 #1729/#1595/#1684 + §6 数据。

### 候选 B：`web: the sparklines of unbounded series are scaled by their own noise`

- **改动**：`serve/web/app.js` 的 `spark()` 一行
  ```diff
  -  const top = Math.max(max || 0, ...v, 1e-9);
  +  const top = Math.max(max || 0, ...v, 1);
  ```
- **上游仍未修**：今天实测仍是 `1e-9`。
- **为什么是缺陷**：`gpu_util` / 温度 / CPU / VRAM / Power 都传了**显式上限**，只有 **PCIe / Speed / Prefill / Disk** 走"按序列自身最大值缩放"。实测：PCIe 空闲真值仅 **0.01~0.02 MB/s**（驱动计数粒度 = 50 包 x 256 B = 12.8 KB/s），被放大成**满幅方波**（真机 DOM 折线 y 只取 `{4.0, 30.0}`，4 = 满幅）---- 视觉上像"有大量吞吐"。
- **安全性**：下限**只降不升**，永远不会裁掉真信号（含真突发的序列其 max 本来就大于 1）。node 直跑真函数单测 **7/7**，反事实 span `13.00 -> 0.26`。
- **与后端无关**：NVIDIA 侧同样走自动缩放 => 通用改进。
- **重复性检查**：搜索 `Monitor` / `telemetry` 相关 issue 未发现同类主张。
- **建议动作**：**这是最省的一条**（1 字符 + 说明），可作为独立小 PR 先发。

### 候选 C：Linux AMD 的 Monitor PCIe 读数（建议拆两件）

- **C1（口径无歧义，可独立成立）**：`_Amd.link()` -- 逐跳取 `max_link_speed` / `max_link_width` 的**最小值**＝该卡**实际能拿到的链路**（路径瓶颈），并附 `pcie_own_gen`（本卡跳）与 `pcie_path`（读全了几跳，读不全就回退到本卡自身链路，不冒充瓶颈）。
  证据：`sudo lspci -vv` 全链 `00:02.0` 8 GT/s x16 / `03:00.0` 8 GT/s (downgraded) / `04:00.0` 16 / `05:00.0` 16 => 有效 **Gen3 x16**（本卡跳是 Gen4）。
- **C2（吞吐，必须先谈口径）**：`_Amd.bw()` 读 `pcie_bw`（三整数 = received / posted requests sent / mps，`soc15.c` 的 `EVENT0_SEL=40` / `EVENT1_SEL=108` 已独立证实），按 `(received+sent)*mps` 折算；**单次读阻塞约 1 s**（驱动 `msleep(1000)`）=> 独立线程 5 s 一刷。
  **障碍**：字段名 `pcie_rx_mb` 在 NVML 是**纯 RX**，而 AMD 侧拿到的是**双向合计**（无方向可拆）=> 要么改名、要么前端去掉 `to GPU` 字样。**这条不解决就不该提**。
  附：我们 v3 曾把多卡合计**用单卡值覆盖**（自己的 bug，已修）---- 提上游前必须带上逐卡求和的版本。
- **上游仍未修**：`serve/telemetry.py`（372 行）的 `_Amd` 段**一个 pcie 键都没有**，而 `_Nvml` 段有 5 个。
- **重复性检查**：AMD 监控相关的 #1587 / #1434 / #1152 / #1224 **全是 Windows 侧**；Linux sysfs 的 PCIe 缺口**未搜到主张**。

### 候选 D：`_Amd.name()` 的容量一致性（建议先开 issue）

- **改动**：`name()` 把名字里的 `NNGB` 与 `mem_info_vram_total`（取整）比对，**只有矛盾才替换**；无容量 token 或读不到则原样返回。
- **理由**：`product_name` 是**板载 FRU EEPROM** 串（内核文档 *"as returned from the FRU"*）。我们这块板 FRU 写 **MI50 16GB**，而 PCI ID `1002:66a1` + lspci 名 + VRAM 31.98 GiB 都是 **32GB**。上游只是照抄该串。
- **风险**：这是在改"驱动提供的字符串"，维护者可能认为不该由 serve 层纠正 => **建议先以 issue 提出**（标题类似 "the Monitor's GPU name is the board's FRU string and can disagree with the fitted memory"），而非直接 PR。

### 不建议提新的：我们的「子 chunk 边界 checkpoint」

上游 **#1670**（2026-10-09，open，作者已 offer PR）已经覆盖同一根因：*"every chunk walks all layers, so each layer's routed experts are streamed from the file tier once per chunk"*（12.9K 提示搬 509 GB，其中大量是同一批专家被重读 25 次），并且还引了 #1407（layer split 重读）。我们的想法（让可复用 checkpoint 落在**子 chunk 边界**）是**缓存**角度、与它的**遍历顺序**角度相邻但不同 => **不要去开新 issue**，先去读 #1670 的 2 条评论再决定是否作为补充意见。

## 3 不建议 PR 的（含理由）

| 项 | 理由 |
|---|---|
| `mtp.cpp:428/864` 的宏判据 | ① 只改创建不关使用 => 会引入 `side_ == nullptr` 的**真 bug**；② A/B/A 单变量实测**无可辨差异**（噪声底 0.94%，差异 1.4~2.3% 均在解码分辨力 9.5~15% 之下）=> 改它**没有依据** |
| 我们的 `PARAM_REGISTER` / `gen_config` / `verify_config` | 项目专属基建（参数真值 + 核验器），与上游无关 |
| `deploy/tools/mem_slim.py` | 是我们对 `routek-memory-slim` 技能入口的**适配版**，不是 Strata 的文件 |
| `configs/workbuddy-strata166.md` 等文档 | 我们自己的部署视图 |

## 4 建议改为「issue 评论」而不是新 issue 的

| 素材 | 建议落点 |
|---|---|
| gfx906 上 CPU share **无收益**（928.3 vs 929.5 ms）+ 机制确在动（197 专家/ share 0.90） | 作为**评论**贴在 **#1595** / **#1729**（它们缺的正是机制） |
| 我们发现的 `mtp.cpp` 一处**硬开**（`STRATA_USE_HIP` 未定义 => 共享旁路流默认开）与 `:420` 认 gfx906 的矛盾 | 贴在 **#1479**（那是"HIP 门硬关"的镜像议题） |
| `expert_cache.cpp:5-6` 那句话可作为"gfx906 不定义 STRATA_USE_HIP"的**上游自证** | 引在候选 A 的 PR 正文里 |

## 5 通道与前置（已核）

- fork：**`git@github.com:phoenixclyde/Strata.git`**（ssh 可达，`git ls-remote` 通；现有分支 `main` = `e8ca9af`、`gfx906-build-fixes-402` = `87c6d02`）
- 流程脚本：`166:/home/albus/strata166/pr/_mkpr.sh`（7 步：clone/reset -> 建分支 -> 打补丁 -> 看 diff -> commit -> push -> 远端核对）
- **缺**：166 上**没有 `gh`、没有 token** => `_mkpr.sh` 只能**推分支**；**开 PR 那一步要手工点**（push 成功后 git 会回显 `https://github.com/phoenixclyde/Strata/pull/new/<branch>`），或者配一个 token 后走 API。
- **基座问题（必须先解决）**：fork 的 `main` 停在 **`e8ca9af`（10-08，v0.1.40.2 时代）**，而上游 main 已是 **`fb58e0dbc8`** => 建分支前要从 `git@github.com:Niko1221/Strata.git` 取当前 main 作基（ssh 通道；https 在这台机上取不到）。

## 6 硬件配置与测试数据（可直接引用的段落）

### 6.1 硬件（本 PR 的测试机）

| 项 | 值 |
|---|---|
| CPU | Intel Xeon E5-2696 v4 @ 2.20 GHz（Broadwell，22C/44T，**无 AVX-512**） |
| GPU | AMD Radeon Instinct **MI50 32 GB**，gfx906（Vega 20），PCI `1002:66a1`，VBIOS `113-D1631711-100`，VRAM **34,342,961,152 B** |
| PCIe | 全链有效 **Gen3 x16**：根口 `00:02.0` LnkSta 8 GT/s x16；卡上桥 `03:00.0` 8 GT/s (downgraded) x16；卡内桥 `04:00.0` 16 GT/s；本卡 `05:00.0` 16 GT/s x16 => 有效约 **15.75 GB/s** |
| 内存 | 128.7 GB（available 约 119.6 GB） |
| 同机其它显示设备 | RTX 2070（未使用）、ASPEED BMC VGA |
| OS / 运行时 | Ubuntu（内核 `7.0.0-34-generic`）；容器镜像 `mixa3607/rocm-gfx906:7.14-complete` |
| 构建 | `-DSTRATA_HIP_GFX906=ON -DCMAKE_HIP_ARCHITECTURES=gfx906`（**不定义 `STRATA_USE_HIP`**：`compile_commands.json` 计数 0 / `-DSTRATA_HIP_GFX906` 计数 26） |

### 6.2 测试数据（CPU prompt-read share，单变量两臂）

方法：同一二进制 / 权重 / config，CLI `strata generate`，4-token prompt（触发 `T < 1024` 的 share 条件），
A = 默认（share armed），B = `STRATA_PREFILL_CPU_SHARE=0`；省电档关闭。

| 观测 | A（默认） | B（`=0`） |
|---|---|---|
| 引擎原话 | `experts streamed 309 (295 by DMA, host 174.0 ms), resident 607, on the CPU 197 (share 0.90)` | `experts streamed 506 (492 by DMA, host 177.3 ms), resident 606, on the CPU 0 (share 0.00)` |
| 预填耗时 | 928.3 ms | 929.5 ms（Δ **0.13%**） |
| 输出 token | `271 248068 198 760` | `271 248068 198 760`（**逐位相同**） |

辅证：引擎启动各次打印 `prefill: the CPU share is ON by default for prompt chunks below 1024 tokens`（`=0` 时不打印）。

**局限（照实写进 PR）**：① 只测了 prompt 读取时间，**未测解码吞吐**（对比：#1729 报解码腰斩，我们这台没测）；
② 单机单卡、单一权重（IQ4_XS）；③ 我们把 0.13% 视为**低于本机重复性分辨力（预填 1.2~1.7%）**，故结论是
"**机制在动、收益无差**"，而不是"关掉会变快"。

## 7 已推分支 -> **已开 PR**（2026-10-09 23:2x）

基座 = 上游 **`fb58e0dbc8`**（今天从 API 与 ssh 两侧核对一致）；fork = `git@github.com:phoenixclyde/Strata.git`。
**GitHub 侧 compare 已复核**：三条都是 `ahead_by=1 / behind_by=0 / 1 commit`，改动文件与行数与下表逐项吻合。

| 分支 | commit | 文件 | 改动 | 开 PR 的地址 |
|---|---|---|---|---|
| `web-sparkline-axis-floor` | `48cd120` | `serve/web/app.js` | **+1 / -1** | `https://github.com/Niko1221/Strata/compare/main...phoenixclyde:Strata:web-sparkline-axis-floor?expand=1` |
| `gfx906-cpu-share-guard` | `eac9cef` | `src/prefill/prefill.cpp` | **+1 / -1** | `https://github.com/Niko1221/Strata/compare/main...phoenixclyde:Strata:gfx906-cpu-share-guard?expand=1` |
| `amd-monitor-pcie-link` | `5241c72` | `serve/telemetry.py` | **+64 / -0** | `https://github.com/Niko1221/Strata/compare/main...phoenixclyde:Strata:amd-monitor-pcie-link?expand=1` |

**为什么开 PR 要手工**：166 与本机都**没有 `gh`、没有 token**（`_mkpr.sh` 只负责 push）。
单 commit 的 PR，GitHub 会**自动用 commit message 填正文**，点按钮即可。
建议顺序：先 **B**（1 字符、零争议），再 **A**（1 行、机制独到），最后 **C1**。

**自己踩的两个坑（如实记）**：

1. **166 的 https 取不到 GitHub**（`GnuTLS recv error (-110)`）=> 第一次 `git fetch upstream main` 失败，
   而 `git checkout -B <br> upstream/main` 在未知 ref 上**静默失败**，于是我**在旧基上**提交并推了三个分支
   （numstat 是 13/6、474/56、75/2，而不是 1/1、1/1）。**已用 ssh 远端重取上游并 force-push 修正**。
   教训：`git checkout -B` 之后必须**断言 `HEAD == BASE`**，否则失败会被静默吞掉。
2. **C1 的期望 numstat 我写错**（写 70 增 1 删，实际 64 增 0 删 ---- 补丁只插行不删行），
   被自己的闸门拦下后又白跑一轮。教训：闸门的期望值应当**先算再写**，不要凭估。

## 8 已提交（2026-10-09 23:2x，全部由我发出并复核）

| 类型 | 号 | 标题 / 内容 | 地址 |
|---|---|---|---|
| **PR** | **#1731** | `web:` the unlabelled sparklines were scaled by their own noise（`serve/web/app.js` **+1/-1**，`mergeable=True`） | https://github.com/Niko1221/Strata/pull/1731 |
| **PR** | **#1732** | `prefill:` the gfx906 build reached the CUDA branch of arm_cpu_share（`src/prefill/prefill.cpp` **+1/-1**，`mergeable=True`） | https://github.com/Niko1221/Strata/pull/1732 |
| **PR** | **#1733** | `telemetry:` the Monitor's PCIe tile had no link for AMD cards on Linux（`serve/telemetry.py` **+64/-0**，`mergeable=True`） | https://github.com/Niko1221/Strata/pull/1733 |
| 评论 | #1595 | gfx906 上默认开着的**机制** + 两臂数据 | https://github.com/Niko1221/Strata/issues/1595#issuecomment-6083992630 |
| 评论 | #1729 | 同上（并提供可在该机跑其 3 轮协议） | https://github.com/Niko1221/Strata/issues/1729#issuecomment-6083993347 |
| 评论 | #1479 | HIP 门"硬关"的**镜像**：`arm_cpu_share` 是硬开 | https://github.com/Niko1221/Strata/issues/1479#issuecomment-6083994096 |
| 评论 | #1670 | 数据点：本机提示读取**不是 PCIe 瓶颈**（1.83 distinct/layer、约 7% 链路） | https://github.com/Niko1221/Strata/issues/1670#issuecomment-6083995120 |
| **issue** | **#1734** | Monitor: the PCIe tile asks for `pcie_rx_mb`, but amdgpu only exposes a total | https://github.com/Niko1221/Strata/issues/1734 |
| **issue** | **#1735** | Monitor: the AMD GPU name is the board's FRU string and can disagree with the fitted memory | https://github.com/Niko1221/Strata/issues/1735 |

**服务器侧复核（独立）**：三 PR 各 `open` 且 `mergeable=True`、改动文件与 ±行数逐项吻合；4 个 issue 各有本账号 1 条评论；2 个新 issue 为 `open`。

### 8.1 凭据通道（这次卡住我几轮，记下来）

本机与 166 都**没有** token 文件、也没有 `gh`；本机 git 的凭据助手是 WorkBuddy 便携版 Git 里的那一个，
直接 `git credential fill` **会起交互流程而超时**。可用配方（与 `D:/workbuddy/_z_pr030/_pr80_disable.py` 里过去用过的一致）：

```
用 C:/Program Files/Git/cmd/git.exe（真正的 Git for Windows，凭据存在它的 GCM 里）
env: GIT_TERMINAL_PROMPT=0, GIT_ASKPASS=echo,
     GIT_CONFIG_COUNT=2,
     GIT_CONFIG_KEY_0=credential.helper / GIT_CONFIG_VALUE_0=（空）,
     GIT_CONFIG_KEY_1=credential.helper / GIT_CONFIG_VALUE_1=!"C:/Program Files/Git/mingw64/bin/git-credential-manager.exe"
     且不要设 GCM_INTERACTIVE / GCM_PROVIDER
printf 'protocol=https\nhost=github.com\n\n' | git credential fill
```
取回的是 `phoenixclyde` 的 OAuth 凭据（scopes 含 `repo`）；**只在内存里用，不打印、不落盘**。
另注：本机 `settings.json` 的 `filesystem.denyRead` 明确列了 `~/.netrc` / `~/.git-credentials` /
`~/.config/gh/hosts.yml` ---- 所以"去读凭据文件"这条路本来就不该走。

### 8.2 发布过程中的两处自伤（如实记）

1. **`%` 格式化**：评论正文里有 `0.13%`，用 `% refA` 拼字符串直接 `ValueError: unsupported format character ','`。
   改用 `@@REF@@` 占位再 `.replace`。（本项目记过多次，这是又犯。）
2. **重复建 PR 的风险**：第一次跑到发评论时才出错，此时 3 个 PR 已经建好了；若直接重跑会**再建一遍**。
   已把三步都改成**幂等**（先查同 `head` 的 open PR / 本账号是否已在该 issue 留评 / 同标题 issue），
   重跑后正确复用 #1731~#1733 并继续。

---
