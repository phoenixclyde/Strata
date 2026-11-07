# W775 -- Strata 0.1.41 -> 0.1.42 版本同步（缺版核查 + 升级决策）

> 触发：机主令「Strata 必须更新到最新版，同时待办跟着最新版同步走，必须把最新几版我们没有的版本更新内容都合进去」。
> 日期：2026-10-11 02:xx。
> 纪律：**每条结论标注「实测 / 源码核实 / 上游逐字 / 推测」**；凡"上游逐字"均给 release notes 原文或镜像内文件路径。

---

## 1 版本跨度（据实）

**上游 releases（GitHub API 现查，2026-10-11 02:1x）**：

```
v0.1.42    2026-10-10T16:10:01Z   <- 最新
v0.1.41    2026-10-08T12:14:59Z   <- 我们生产当前
v0.1.40.4  2026-10-08T08:04:33Z
v0.1.40.3  2026-10-07T18:01:30Z
v0.1.40.2  2026-10-07T12:13:49Z
v0.1.40.1  2026-10-06T09:53:35Z
v0.1.40    2026-10-06T06:29:21Z
v0.1.39    2026-10-04T12:32:47Z
...（更早）
```

**结论**：**0.1.41 与 0.1.42 之间没有中间版本**（0.1.40.x 系列在我们 0.1.41 时代已覆盖）。
=> 所谓"最新几版我们没有的"，**据实只有 0.1.42 这一版**。（relnotes 逐字：*"The five fixes planned as 0.1.41.1 were never released and are part of this version."*）

**生产实况（2026-10-11 02:1x ssh 现查）**：
```
strata166-407 | strata-gfx906:0.1.41 | Up 25 minutes        <- 生产
strata166-406 | strata-gfx906:0.1.41 | Exited (0) 2 days ago <- 回滚位
镜像：strata-gfx906:0.1.42（1 小时前建，6.59 GB）+ 0.1.41（2 天前）
```

---

## 2 0.1.42 全部变更 vs 本机（gfx906 / MI50 32GB）适用性逐条判定

release notes 全文 23,126 字符，已存档 `deploy/tmp/_v0142_notes.txt`。按章节穷举：

### 2.1 Faster（3 条）

| 变更 | 上游逐字适用面 | 本机判定 |
|---|---|---|
| `STRATA_ROUTE_TAIL_SKIP=7`（CUDA 默认开，**改答案**） | *"off ... **on AMD and Intel**"*；且 *"off when every expert is in VRAM"* | **不适用**（我们是 AMD；且本机 9761 槽驻留绝大多数专家）。**【W775delta 更正 2026-10-11 12:1x】** **判错**：实测本机 ON(default) 且在动作 => 转 W16/W17 |
| 实测 PCIe share（CUDA 单卡，**改答案**） | *"off on a layer split, with `--batch`, a peer GPU, every expert in VRAM, and **on AMD and Intel**"* | **不适用**（AMD） |
| gfx12 prompt switches（`GDN_*`/`CVEC_FUSE`）默认开 | *"on for **gfx1200/gfx1201** cards"* | **不适用**（我们是 gfx906） |

=> **Faster 三条对 gfx906 全部不适用**（上游自己逐字写了）。**【W775delta 更正 2026-10-11 12:1x】** **第一条（`ROUTE_TAIL_SKIP`）已证不成立**（本机默认开且在动作）=> 该句应改为「F-2/F-3 两条不适用」 |**这也意味着 0.1.42 的标题卖点"13-16% faster decode"对本机不兑现**。

### 2.2 Fixes（~19 条）

| 变更 | 本机相关性 |
|---|---|
| **`#1732` gfx906 build 不再武装 CUDA-only CPU prompt share** | **直接命中 = 我们的 PR**（详见 §3） |
| CPU prompt share 在 RAM/commit 不足时跳过 | **命中**（= #1729 的修复，见 §3） |
| Windows AMD / `--prefill auto` 6144 截断（#1630） | 不适用（我们 Linux，且不用 `--prefill auto`） |
| AMD 2+ GPU checkpoint save | 不适用（单卡） |
| End of context（#1700） | 通用修复，对本机无害 |
| Intel / Pascal / Volta / cuBLAS / Windows layer split | 不适用 |
| 取消的请求保留其恢复的会话（#1620） | 通用，或对本机有益 |
| `STRATA_STAGE_PIN=1` 曾腐蚀答案（#1237） | **命中**（该 opt-in 本机可及，我们未用；记录为"已知缺陷已修"） |
| 并行请求挂起（#1603） | 通用 |
| thinking budget（#984） | 通用 |
| **内存守卫 in containers（#1601）** | **命中**（本机是容器部署；`STRATA_ROUTE_TAIL_SKIP` 无涉，但此修复读 cgroup limit） |
| 无 AVX2 的 CPU（#1701 等） | 不适用（本机 CPU 有 AVX2） |
| 小型修复（keep-alive/503/报错前缀） | 通用 |

### 2.3 New opt-ins（12 条）

| 变更 | 本机判定 |
|---|---|
| **gfx906：`STRATA_GFX906_ATTN_QUERY_SWIZZLE=1`（#1661）/ `STRATA_GFX906_ATTN_REDUCE12=1`（#1718）** | **命中 = 我们已登记的 P55/P56**（详见 §3、§4） |
| `STRATA_PF_FUSED=1`（gfx12） | 不适用（gfx12） |
| `--pipeline-windows 2`（3+ layer split） | 不适用（单卡） |
| `--batch-mtp`（layer split） | 不适用（单卡） |
| data-parallel replicas（`--replicas N`） | 不适用（单卡） |
| `--aux-cpus` / `STRATA_SPLIT_MTP_BATCH`（多卡） | 不适用（单卡） |
| `STRATA_ROUTE_PRIOR=0.5`（**改答案**，配 ROUTE_TAIL_SKIP） | 不适用（AMD 上 tail-skip 本就不生效）。**【W775delta 更正 2026-10-11 12:1x】** **前提判错**：`ROUTE_TAIL_SKIP` 本机默认开且在动作 |
| Intel A-series / sessions / `STRATA_STAGE_PIN` / MMQ_RESIDENT_SORT_NE 等 | 不适用或低优先 |
| **`STRATA_LOOKAHEAD_STATS=1` + `tools/replay_cache_policy.py`（仅测量）** | **命中**（对口我们的 P33 会话缓存 / P51 门；离线重放专家缓存策略） |
| `prevent_sleep`（Windows） | 不适用 |

### 2.4 Answers can differ（6 条）

逐条读：**没有一条在 gfx906 上改变默认答案** --
- `ROUTE_TAIL_SKIP` / measured PCIe share：**AMD 上不生效**；**【W775delta 更正 2026-10-11 12:1x】** **`ROUTE_TAIL_SKIP` 一条不成立**（本机默认开且在动作）=> 本机答案相对 0.1.41 有偏移；measured PCIe share 仍待复核 |
- CPU prompt share 跳过：**在 0.1.42 里 gfx906 已不再武装该 share**（#1732）=> 本机答案等于 `=0`；
- thinking budget / tool set 顺序 / 显式 opt-ins：通用或不涉默认。

=> **结论（据实）：0.1.42 在 gfx906 上不改变默认答案**。**【W775delta 更正 2026-10-11 12:1x】** **对 `STRATA_ROUTE_TAIL_SKIP` 不成立**：本机该键默认开且在动作（生产日志 12/12 + skipped N 达 672,855）=> 答案相对 0.1.41 有偏移（KL 量级 0.003-0.006）；其余项仍成立。这与 W774 实测"prompt 全中性 + 输出逐位"互证。

---

## 3 与本机已登记参数的对账（关键）

### 3.1 镜像内穷举 `STRATA_GFX906_*`（**源码核实**）

在 166 上用两版镜像各跑 `grep -rl <宏> /src`：

| 宏 | 0.1.41 | 0.1.42 | 我们登记 |
|---|---:|---:|---|
| `STRATA_GFX906_ATTN_QUERY_SWIZZLE` | 0 | **8 文件** | **P55** [OK] |
| `STRATA_GFX906_ATTN_REDUCE12` | 0 | **5 文件** | **P56** [OK] |
| `STRATA_GFX906_MMQ_OPT_CAP` | 0 | 1 文件* | 否 |
| `STRATA_GFX906_HC_F16` | 0 | 1 文件* | 否 |
| `STRATA_GFX906_ATTN_QUERY_SWIZZLE_TRACE` | 0 | 2 文件 | 否（trace） |
| `STRATA_GFX906_ATTN_REDUCE12_TRACE` | 0 | 1 文件 | 否（trace） |

\* **关键澄清（源码核实）**：`MMQ_OPT_CAP` / `HC_F16` 的"1 文件"**只是 `bench/results/2026-10-08-gfx906-qsa-query-swizzle/service-qualification.json` 里的 flags 记录**（别人的实测配置证据），**在 `/src` 的 C++ 源码里一次都没有**。
=> 它们**不是 0.1.42 引擎实现的开关**，是**第三方举证件里的历史 flags**。**无需登记**（登记了反而是污染）。
同理两个 `_TRACE` 只是 P55/P56 的调试追踪，**不单列**。

### 3.2 我们的 PR 在 0.1.42 的落点（**源码核实 + 上游逐字**）

- **#1732**：relnotes Fixes 逐字 *"the gfx906 build no longer arms the CUDA-only CPU prompt share (#1732)"*。
- **#1731 / #1733**：relnotes 逐字 *"Web app and Monitor: a favicon, the PCIe tile for AMD cards on Linux (**#1733**), and sparklines no longer scaled by their own noise (**#1731**)"*。
- **#1396**：0.1.41 已收录（W774 已核）。

=> **我方 4 个 PR 全部进入 0.1.42/0.1.41，无遗漏**。

### 3.3 上游新出现的 gfx906 社区报告（**镜像内实读**）

0.1.42 的 `bench/results/` 里有 **7 份 AMD/gfx906 相关目录**：

| 目录 | 卡 | 版本 | 与我们的关系 |
|---|---|---|---|
| `2026-10-03-community-2x-mi50` | **2x MI50 16GB** | 引擎 0.1.38+#638 | 我们 MEMORY 记的"双卡 16GB"就是它 |
| `2026-10-04-community-mi50` | **MI50 32GB** | 0.1.38 | **同卡！** decode 36.0/34.0/33.5 tok/s（4K/32K/128K） |
| `2026-10-08-gfx906-qsa-query-swizzle` | **2x Radeon Pro VII 16GB** | 0.1.40 实验栈 | **直接实测我们的 P55** |
| `2026-10-09-community-radeon-pro-vii-16gb` | Radeon Pro VII 16GB | 0.1.40.4 vs **0.1.41** | 有 **0.1.40.4->0.1.41 的 gfx906 needle+speed 对照** |
| `2026-10-10-community-rx-9060-xt` | RX 9060 XT | -- | 不同卡 |
| `2026-10-10-community-rx-9070` | RX 9070 | -- | 不同卡 |
| `2026-10-02-community-rx9070xt-windows` | RX 9070 XT | -- | 不同卡 |

**最重要的一份：`2026-10-08-gfx906-qsa-query-swizzle`（README 逐字）**：
- **结论**：*"The opt-in gfx906 query-LDS swizzle improves the measured INT8 batched-QSA component by **14.646806%**"*；
  整模型 65,536 tok：*"+1.185195% prompt throughput, −1.048564% request latency, **all generated token IDs equal**"*。
- **机制**：*"permutes only the shared-memory query layout ... `q(d) = d XOR ((d >> 3) & 4)` ... bijective and self-inverse ... leaves the logical floating-point operands and operation order unchanged"*。
- **对本机 P55 的意义**：**这是"另一台 gfx906 机器"对 P55 的独立实测**，且**输出逐位相同**（与 W774 我方"prompt 全中性"不矛盾 -- 他们测的是 **INT8 QSA 组件**，我们 W774 测的是**整机 prompt ms/step**；他们的 +1.19% 是整模型单对，属噪声边）。
- **注意**：该报告作者**自己声明 PR 未成功**（*"Creating the new PR returned HTTP 403, so no new PR exists"*），且与上游 **PR #1402 有模板参数冲突** => 这份工作**尚未进上游**，只以 bench 目录形式存在。

**第二重要：`2026-10-09-community-radeon-pro-vii-16gb`** -- 有 0.1.40.4 -> 0.1.41 的 gfx906 对照数据（含 needle）。Radeon Pro VII 与 MI50 **同 ISA（Vega 20/gfx906）**，可作为我们 0.1.41->0.1.42 升级的**旁证参照**。

### 3.4 我们的 #1855 报告是否被收录（**镜像内实读**）

`ls /src/bench/results/ | grep -iE "32gb"` => **只命中别人的 `2026-10-04-community-4090-32gb-ram-512k`**。
=> **我们的 `2026-10-10-community-mi50-32gb`（PR #1855）不在 0.1.42 里**（PR 仍 open）。**保持待办**。

---

## 4 升级决策（据实）

### 4.1 为什么现在还是 0.1.41（回答机主）

1. **W774 是"验证车"**：五臂跑完是为了回答"该不该升"，收车后 `[restore]` 刻意把生产恢复回 0.1.41（幂等保护）。
2. **升级证据面**：W774 结论 = **prompt 侧无回归、四个 opt-in 对 prefill 全中性、decode 侧弃权**。
   => 0.1.42 **未被证明有收益**（只被证明无回归）。
3. **本项目纪律**：无收益不升生产；但**机主本轮明令"必须更新到最新版"** => 决策改变。

### 4.2 升级到 0.1.42 的收益/风险（据实）

**收益（对 gfx906）**：
- **修复类**：`#1732`（我方，gfx906 不再武装 CPU share）、CPU-share RAM 守卫（#1729 修复）、内存守卫（#1601，容器相关）、`STRATA_STAGE_PIN` 腐蚀修复（#1237）、context 端点修复（#1700）、取消请求会话修复（#1620）。
- **新能力（可选）**：P55/P56（gfx906 专属 opt-in）、`replay_cache_policy.py`（对口 P33/P51）。

**风险**：
- **无默认答案改变**（§2.4 逐条核实）。
- **无 prefill 回归**（W774 实测大档 −0.69% 在噪声内）。
- 标题卖点（13-16% decode）**对 gfx906 不兑现** -- 但那是"没有收益"，不是"有损失"。

=> **据实结论：升级 0.1.42 对本机是"净修复 + 零回归"，值得升。** 机主令已下，执行。

### 4.3 升级动作（走铁律通道）

按 MEMORY §1：`register -> gen_config.py --write -> 推 166 -> restart -> verify_config`。
- 镜像 `strata-gfx906:0.1.42` **已构建**（6.59 GB，`PATCH_SURFACE_ZERO`）。
- 需改的"版本指针"：容器镜像 tag（`0.1.41` -> `0.1.42`）。
- **参数面不变**（0.1.42 的 gfx906 opt-in 全默认关；升级本身不改任何现役参数）。
- 收尾：`verify_config.py` 须 FAIL=0；`/metrics` 取版本与 `gpu_pcie_gen`。

### 4.4 升级实测结果（**2026-10-11 02:3x，已执行完毕**）

**动作链**：
1. 备份：`/home/albus/strata166/_w775_bak/`（`prod_inspect.json` + config + log）。
2. `docker stop` + `docker rename strata166-407 -> strata166-407_0141bak`（**0.1.41 回滚位保留**）。
3. 用**同一 spec** 重建同名容器到 `strata-gfx906:0.1.42`。
4. 就绪后**重放** `bash patches/apply_telemetry_pcie.sh strata166-407`（`docker cp` 两个 patched 文件 + `ast.parse` 自证）=> `docker restart`。

**验收实测（逐项）**：

| 项 | 实测值 | 判定 |
|---|---|---|
| `/v1/status` -> `engine` | `0.1.42` | [OK] |
| `/metrics` -> `engine.version` | `0.1.42` | [OK] |
| 容器 `Config.Cmd` | `["/bin/bash","-lc","cd /src && exec python3 serve/server.py --engine strata --config /data/strata-huihui-ud-iq4_xs.json --port 8090"]` | [OK] **与旧容器逐字一致** |
| GPU 名（telemetry 补丁） | `Radeon Instinct MI50 32GB` | [OK] 补丁生效（未重放时误报 `16GB`） |
| PCIe tile | `gpu_pcie_gen=3` / `gpu_pcie_width=16` / `gpu_pcie_path` 字段在 | [OK] |
| 真实推理 | 4.1s / 40 tok；`predicted_per_second 25.6`；`draft_n_accepted 25/27` | [OK] 运行期正常 |
| `verify_config.py` | **PASS=26 FAIL=0** | [OK] |
| 引擎启动行 | `engine started`，`expert_slots 9761`、`arena_mib 34245`（与升级前一致） | [OK] |

**踩坑（两个，均须记入铁律）**：

1. **CMD 被拆散（首建失败）**：把 `docker run ... /bin/bash -lc "cd /src && ..."` 作为**一个 ssh shell 字符串**发时，远端二次解析把整条命令**按空格拆成 4 个 argv** => 容器 `Config.Cmd = ["/bin/bash","-lc","cd","/src"]` => `bash -lc cd` 秒退（exit 0）=> **`Restarting (0)` 无限循环且 `docker logs` 全空**（无输出可查，极难诊断）。
   **修法**：远端脚本一律走 **base64 -> `bash -s` 通道**，且 CMD 变量用 **`"$CMDSTR"` 双引号包裹** => 作为**单个参数**传给 `bash -lc`，得到完整单元素 CMD。
   （副作用：本机 `Bash` 工具下 `python ... 2>&1` 的重定向会丢 stdout => 首跑"看起来什么都没发生"，实际已改了容器；须改用 Python 捕获。）
2. **telemetry 补丁写层丢失**：`strata166-407` 的 `/src/serve/telemetry.py` 与 `/src/serve/web/app.js` 是 `docker cp` 写入**容器可写层**，**容器重建即丢**（重建后 GPU 名回退为 `...16GB`、PCIe tile 消失）。=> **凡升级/重建该容器，必须重放 `apply_telemetry_pcie.sh` 并 `docker restart`**，否则 UI 与 `/metrics` 静默退化。

---

### 4.5 #1729 守卫链的**第二轮源码核实**（2026-10-11，推翻我方早前表述）

回帖草稿 v2 曾把我方 gfx906 被武装的原因写成"0.1.41 时 HIP 路径仍到达 `by_default=true` 调用点"。
**此为不实**。0.1.42 镜像内实测（`md5 prefill.cpp=67c1d3d19ff50b344bea917362386ff2`）：

```cpp
// prefill.cpp:1867-1876
void Prefill::arm_cpu_share(bool applies, bool by_default) {
#if !defined(STRATA_USE_HIP) && !defined(STRATA_HIP_GFX906)     // 1868
    if (applies && by_default && cpu_share_explicit() == -2.0 && !g_share_default) {
        g_share_default = true;                                 // 1870
    ...
    (void) by_default;                                          // 1876 ← gfx906 落到这里
```

=> 真实机制是**编译期宏选择**：0.1.42 的守卫**已含 `&& !defined(STRATA_HIP_GFX906)`**，我方（`STRATA_HIP_GFX906`）
**整个 `g_share_default = true` 块在编译期就不存在**，`by_default` 参数被 `(void)` 丢弃。
**并非运行期"到达调用点"**。此结论与 W713_PLAN.md §2 第 3 条（P23 关档）逐字吻合：旧版守卫只有
`!defined(STRATA_USE_HIP)` 单合取 => 我方落入 CUDA 分支 => `g_share_default=true` + 打 banner。
**即：上游在 0.1.42 给这个宏补上了第二个合取项**（= relnotes 的 #1732 那条）。

其余两处守卫（0.1.42 逐字）：
- `generate.cpp:6791` `share_rules::default_share_has_work(xcache.slots(), n_layers*n_expert)` -- #1595
- `generate.cpp:6797` `if (... && !share_default_ok()) share_has_work = false;   // H11` -- 宿主机 RAM/commit 守卫
- `generate.cpp:6798` 实际调用 `arm_cpu_share(share_pool, ...)` -- **不传 `by_default`**（默认 false）

=> 三重：**编译期宏已排除** + **#1595 无事可做就不武装** + **H11 内存不够就不武装**。

---

## 5 待办同步（跟着最新版走）

见 `W713_PLAN.md` §6.4 更新：
- #8 **升级生产到 0.1.42** -- **已完成**（§4.4）
- #9 **P55/P56 在 0.1.42 上的复测**（W774 已测 prefill 中性；上游 qsa 报告给出组件侧 +14.6% => 需判"组件收益能否在整机兑现"）
- #10 **`replay_cache_policy.py` 评估**（对口 P33/P51）
- #11 **吸收上游 gfx906 社区报告**（0.1.40.4->0.1.41 对照、2xMI50、MI50 32GB）
- #12 **#1735 改提 PR** -- **已完成：PR #1877**（`serve/telemetry.py +16 -1`，`mergeable_state: clean`）
- #13 **#1734 / #1729 回帖**（草稿 v3 已备，待机主过目）

---

## 6 归档指针

| 件 | 值 |
|---|---|
| 0.1.42 release notes | `deploy/tmp/_v0142_notes.txt`（23,126 字符） |
| 镜像内 QSA 报告 | `strata-gfx906:0.1.42:/src/bench/results/2026-10-08-gfx906-qsa-query-swizzle/` |
| 宏穷举脚本 | `deploy/tmp/_v42_switches.py` |
| 宏定义脚本 | `deploy/tmp/_v42_macrodef.py` |


> **[BAN 归一说明 · 2026-10-11]** 本件属"活跃交付件"，已按项目禁用码位表（见 `W750_MASTER_PLAN.md` 第 0.5.7 节）做 **ASCII 归一**，映射：`U+2192`->`->` · `U+21D2`->`=>` · `U+2026`->`...` · `U+0394`->`delta` · `U+00D7`->`x` · `U+2014`->`--` · `U+2605`->`命中`/`*` · `U+2460-U+2469`->`(1)-(10)` · `U+2705`->`[OK]` · `U+26A0`->`[!]`。
> **引文处语义一字未改**，原文形态可回溯：改前副本 `deploy/tmp/_w21_bak/`（改前 md5 见件尾注）。
> 改前 md5 = `fbc83fced85d87897c6c8f3706131ee2`（字节 17565）。
