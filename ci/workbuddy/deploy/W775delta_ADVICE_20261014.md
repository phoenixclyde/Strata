# W775delta · 全面建议（2026-10-14）

> **输入**：本日「上游邮件 + 提交现状」对照（`W775delta_UPSTREAM_MAILCHECK_20261014.md`）· 生产日志本机副本（40 次引擎启动，2026-10-08 17:52 至 10-11 09:37）· `deploy/tmp/src142/` 源码 · 上游 0.1.43 / 0.1.43.1 / 0.1.44 / 0.1.44.1 发布说明。
> **口径**：事实标来源（实测 / 源码 / 上游逐字 / 推测）。风险按"会不会伤生产 + 可否回滚"评。

---

## 0 一句话结论

**唯一一条"不动版本、可能直接改善生产"的事，是我们自己账本记错了的那条 PLE 路径（`--ple-io`）；它应该先测，其余全是账本/跟进类，不急着动。**

---

## 1 优先级总表

| 序 | 项 | 类 | 成本 | 预期收益 | 风险 | 建议 |
|---|---|---|---|---|---|---|
| **1** | **W29 `--ple-io direct` 对照车** | 生产实测 | 停机 6-10 min | **未测**（上游同类盘量到 prompt 约 7x） | 低（回滚路径已跑熟） | **做** |
| **2** | **W30 `--ple-inflight` / `--ple-row-cache` 同车加臂** | 生产实测 | 同一窗口 | 未测（源码注释称 inflight 64 会让盘半闲） | 低 | **同车做**（3 臂声明清楚） |
| **3** | **W31 `#1984` 只读监控** | 观测 | 0 停机 | 早期发现引擎被 watchdog 重启 | 无 | **做**（一个脚本） |
| **4** | **W32 0.1.43 - 0.1.44.1 逐条台账** | 离线 | 0 停机 | 为升版决策提供依据 | 无 | **做**（升版前置） |
| **5** | **升版到 0.1.43.1 或 0.1.44.1** | 基础设施 | 停机 30-60 min | 拿到 #1984/#2040 等通用修复 | 中（需全量回归） | **待 W32 后再定** |
| **6** | PR #1855 重跑成上游标准口径 | 上游 | 与升版绑定 | 保住 gfx906 单卡 262k 的可见度 | 低 | **绑升版** |
| **7** | PR #1877 rebase 到新版本 | 上游 | 低 | 让评审无阻力 | 低 | **绑升版** |
| **8** | issue #1926 跟进 | 上游 | 低 | 低（见 §4） | 低 | **暂不发** |
| **9** | issue #1923 跟进 | 上游 | 低 | 很低（见 §4） | 低 | **不救** |

---

## 2 生产侧（本机）

### W29 `--ple-io direct` 对照车（**最高优先**）

**事实链**（全部实测/源码）：
- 166 磁盘 = `Fanxiang S100Pro`，`lsblk` `ROTA=0`，**SATA SSD**，XFS on `/`。
- 0.1.42 启动探针实读 **14,560 / 13,268 rows/s**（生产日志 L2720 / L2776），**低于 15,000 的 bar** 故被自动切成 `mmap`。
- bar 的源码：`generate.cpp:3091` `constexpr double kSlowRowsPerS = 15000.0;  // ~60 MB/s of 4 KiB pages; a healthy NVMe is >100k`。
- 上游 0.1.43.1 `#2040` 逐字判该自动切换在慢盘上**错误**：*"Its 15,000 rows/s bar was set on NVMe drives; a SATA SSD tops out at 10-14K rows/s with direct reads and the switch to mmap made its prompts about 7x slower（77.8K prompt: 884 tok/s direct vs 76-154 mapped）"*。0.1.43.1 的修法是**检查只警告、不再自动切**。
- `--ple-io direct` 是 **0.1.42 内置**开关（help 实读 `--ple-io direct|mmap|ram`）=> **不必升版**。
- 我们**从未**测过 direct 臂：register `P91` 只测了 `STRATA_PLE_IO=ram`（**-45% REJECTED**），那是第三种臂。

**设计**（沿用本项目单变量纪律）：
- **臂：A = 现状（不传 `--ple-io`，引擎自动 mmap）/ B = `--ple-io direct`**；可选 **C = `--ple-io direct --ple-inflight 512`**（源码注释：`64 left the SSD half idle (32K: 303 -> 189 ms)`，默认 256）。
- **形状**：同 pack / 同 config 其余项字节相同 / `--kv k8v4` / `Z0=off`；档位取 **短（约 3-5K）与长（约 64K 或 93K，与我们 #1855 的第三档对齐）**；每臂 **5+ runs**（本项目 decode spread 惯常 16-41%）；读**引擎自己的 timing 行**。
- **温差控制**：先排除冷热（我们已知 `drop_caches` 不重置 mmap 活跃页 => 必须**交替 ABBA**，且记录每次的 `file tier` / page cache 行）。
- **验收判据**：prompt tok/s 的**跨臂区间**（不是单点）+ **`io prefetch` / PLE 行**的形态变化 + **输出 token id 一致**（PLE 只影响速度，不应改答案；若改答案则立即停）。
- **成本**：临时实例 + 生产停止 6-10 min，沿用 W4 那套（config 副本 + `-e` 注入，生产 config/日志不碰，完事 `docker start` 恢复）。
- **风险与回滚**：低。唯一真实风险是"测出来 direct 更慢"——那也是结论，价值不减。

### W31 `#1984` 只读监控（零停机）

- `#1984` 现象：长 prompt 停在 `layer 1 of the prompt chunk` 并重启引擎（根因：自动切 mmap + 60 s watchdog）。
- **我们目前的实测**：本机日志该特征串命中 **0 次**；生产容器 **Up 3 days**。=> **当前无此问题**，但样本只到 10-11 09:37。
- **建议**：加一个只读巡检（扫 `layer 1 of the prompt chunk` / `restarting the engine` / engine 启动计数），与现有巡检合并；**这是"早知道"而不是"现在有事"**。

### 升版纪律（无论何时升）

- **必须重放 `apply_telemetry_pcie.sh`** —— 本地覆写 `serve/telemetry.py` + `web/app.js`，否则 Monitor 的 AMD PCIe 瓦片回退为无数据（0.1.42 升级时的教训，已在账上）。
- 升版后按铁律走：`verify_config` `FAIL=0` + `todo_reconcile --strict` `GAP=0` + 关键参数回归（`--resident-experts` 行为 / `--kv k8v4` / PLE 默认值 / `ROUTE_TAIL_SKIP` 默认）。

---

## 3 版本侧

### 不建议直接升 0.1.43

0.1.43 是被 **0.1.43.1** hotfix 的版本（`#2010` 自适应 overlap 默认又关、`#1964`/`#1975` 桌面解码崩塌、`#2040`/`#1984` 慢盘 prompt）。**升到 0.1.43 等于故意踩已知 bug。**

### 升版候选 = 0.1.43.1 或 0.1.44.1

- 对我们的**答案风险低**：0.1.43 逐字 *"Answers are the same as 0.1.42 (byte-identical on every machine we tested) except where a default below says otherwise"*，而"改了默认"的那些**逐字限定 RDNA4 + Unsloth 文件由 setup 写入的 env** —— 我们既不是 RDNA4，config 也不是 setup 生成的（手写）。0.1.44 同理。
- 对我们的**速度收益也低**：0.1.43 的 AMD 提速逐字限定 RDNA4，并写死 *"RDNA3 (gfx11) and older keep their 0.1.42 behaviour"*。
- 所以升版的**真实动机只有通用修复**：`#1984`/`#2040`（慢盘 prompt + watchdog）、`#2134`（Foresight 丢专家）、`#1587`（Windows，不适用）、`--adapt-async` 扩到 arena、`STRATA_PIN_BY_NEED`（适用性待核）。
- **结论**：**升版的价值主要在"稳定性和口径对齐"，不在速度**。若 W29 证明 `direct` 就是大头，那么"显式在 config 里写 `--ple-io direct`"可能比升版更划算（一行配置 vs 一次全量回归）。**先测，再决定升不升。**

### W32 逐条台账（升版前置，离线）

沿用 `W775delta_REL0142_LEDGER.md` 体例，逐条过 0.1.43 / 0.1.43.1 / 0.1.44 / 0.1.44.1，重点标出**"会覆盖我们 ADOPTED 默认值"**的条目：`STRATA_ROUTE_TAIL_SKIP`（0.1.44 为 Unsloth 文件写 `=0`，前提 "every expert is in RAM"）、`STRATA_PIN_BY_NEED`、`setup` 的 RAM 预算新规则、PLE 自动切换行为变更。

---

## 4 上游侧

| 项 | 建议 | 理由 |
|---|---|---|
| **#1926**（4 条 doc-level notes，0 回复） | **暂不发** | 四条里：(1)(2) 是"请在注释/文档里加一行"；(3) `ROUTE_TAIL_SKIP` 措辞 **上游已在 0.1.43/0.1.44 自行细化**（`=0` where every expert is in RAM、RDNA3 及更老保留 0.1.42 行为）；(4) 需对着 **0.1.44 源码**核，而我们没有 0.1.44 本地树。=> 现在发只能是"我们还没升版、等升了再核"的空话。**上游自己给了路子：升级后以新 issue 链接旧的**（triage 逐字 `A new issue that links this one works too.`） |
| **#1923**（淘汰策略 feature，0 回复） | **不救，让它被关** | 三条独立理由：(a) 维护者 4 天 0 兴趣；(b) **我们自己已撤回动机**（`0.7086` 是 trace 口径，生产实测 95.4-98.0%）；(c) **B7 之后我们的 miss 成本已归零**（文件层 0 blob reads，VRAM miss 落到 RAM 而非盘）=> 这条在我们这里的收益面**已经消失**；且 `ExpertCache::admit` 的 *"it never evicts"* 是**设计性**的（上游把它当测量问题留给 `tools/bench_eviction.py`） |
| **PR #1855**（bench，0 评论） | **绑升版重跑** | 上游社区 bench 已形成**标准口径**：`tools/strata_bench.py`（suite 1，3 runs，medians with ranges）—— 见 #2420（RTX 3090 / 0.1.44.1）、#2116（RTX 5090 D v2 / 0.1.43）。**该工具不在 0.1.42 树里**（src142 的 tools 只有 `needle_bench.py` / `bench_eviction.py` / `replay_cache_policy.py`）=> 要按统一格式提交**必须用新树**。我们 #1855 的数字是 **0.1.41 引擎**，跨 4 个版本会显得过期；而"gfx906 单卡 262k"这个位置目前只有我们占 |
| **PR #1877** | **不动，升版时顺手 rebase** | 其 issue #1735 已被 3 天清理关掉，但这**不影响 PR 本身**进入评审；两条 PR 均 `mergeable_state=clean`，无需现在动作 |
| 已关的 #1670 / #1734 / #1735 / #1595 / #1479 | **不再跟** | 同上批清理；#1595 的修复已进 0.1.42（Niko 逐字确认） |

---

## 5 我们自己的账本 / 待办（本轮新增）

| 新编号 | 内容 | 动作 |
|---|---|---|
| **W29** | `--ple-io direct` 对照车（含 `--ple-inflight` 加臂） | 发车（§2） |
| **W30** | `#1984` 只读巡检 | 脚本 |
| **W31** | 0.1.43 - 0.1.44.1 逐条台账 | 离线 |
| **W32** | 升版评估（W31 之后） | 决策 |
| 追加注记 | **`register P91`** 需加注「只测了 `=ram` 臂；`direct` vs 自动 `mmap` 未测」 | 账本 |
| 追加注记 | **`P70`（Foresight）判定加限定**：上游 0.1.44 `#2134` 修了"Foresight 交换不保留它搬动的专家"这个 bug，我们 `P70` 的 REJECTED 用的是 0.1.42 观测 => 该观测可能被此 bug 污染 | 账本 |
| 追加注记 | **`P57`（`ROUTE_TAIL_SKIP`）在三层结构下重判**：0.1.44 给了两档（全 RAM => `=0`；RAM-budget => 保留 skip），而我们既不是全 RAM（VRAM 9761 槽 + RAM 补集 36.8 GiB + SSD 层）也不是 RAM-budget（`--resident-budget-gib` 已废）=> 落在第三类，**上游未给口径** | 账本 + 可选实测 |

---

## 6 方法论：把本轮的坑变成规则（**建议入铁律**）

1. **「未观测到」!=「不存在」。** 本轮 P0 的根因是**空 grep 结果被读成"代码路径不存在"**。=> 凡下 **"不可达 / 未启用 / 从不执行"** 这类否定结论，必须附**至少一条正向存在性证据**（启动 banner / `/proc` 运行期 / 计数器 / 计数），否则只能写 **"未观测到（观测手段：<命令>）"**。这条是现有铁律「`默认关` != `不可达` != `生产在用` != `有收益`」的补强 —— 再加一格：**`未观测到` != `不存在`**。
2. **grep 模式必须落盘。** 下否定结论时记录**实际使用的正则**，否则后人无法复核"为什么会漏"。本轮漏检的具体原因就是模式 `PLE ... rows/s` 与真实行（行首 `--ple-io`，`rows/s` 在行中）不匹配。
3. **引文与转述要分开标。** 本轮另发现一处（`W28_COLD_PATH_REDESIGN.md` 曾把三条不同请求的字段拼成"逐字行"，AUDIT5 已修）—— 凡自称"逐字"，必须能被单行 grep 命中。

---

## 7 不建议做（含理由）

- **不催 PR**：上游 open PR 队列 20+，两条均无冲突，催只会消耗信任。
- **不重提 #1735**：PR #1877 仍在队列，重开 issue 只会再被 3 天规则扫一次。
- **不因 AMD 提速而升版**：0.1.43 的 AMD 增益逐字限定 RDNA4。
- **不在 0.1.42 上追 `tools/strata_bench.py`**：该工具不在 0.1.42 树里，硬凑会引入自制口径，反而不可比。
- **不动 `--ple-io ram`**：已测 -45%（`P91` REJECTED），表 28.8 GB 锁定进 RAM 不划算。

---

## 8 若你只说"开始"，我按这个顺序跑

1. **W31（离线台账）** —— 0 停机，先把升版面的信息补齐；
2. **W29（`--ple-io direct` 对照车）** —— 一次停机窗口（约 10 min），3 臂 A/B/C，最少 5 runs/臂；
3. **W30（`#1984` 巡检）** —— 脚本挂上；
4. 依据 W29 结果二选一：**(a)** 若 direct 有显著收益 => 改 register（`P91` 加注 + 新项 `--ple-io direct`）+ `gen_config --write` + 推送 + restart + verify（**不升版**）；**(b)** 若 direct 无差异 => 转而做 W32 升版评估；
5. 上述任一完成后按铁律核验并回写 `W750` / `register` / `MEMORY.md`（走技能入口）。

**风险与回滚**：全程只用生产 config 的**副本**，生产 config/日志不碰；临时实例用独立端口；异常即 `docker start strata166-407` 恢复；恢复后核 `config md5 == ff8cb973...` + `/health` + 6 容器。

## 9 追加（2026-10-18 23:50 生产重启实测）

重启后本机启动段出现与 10-10 **相反**的结果：

| 启动时刻 | 探针行 | 结果 |
|---|---|---|
| 2026-10-10 18:27 / 另一次 | `--ple-io direct measures slow here (14560 / 13268 rows/s, about 60 / 54 MB/s)` | **切成 `mmap`** |
| **2026-10-18 23:50** | **`PLE direct read probe: 34235 rows/s (fine)`** | **保留 `direct`** |

同一 config、同一磁盘、同一 bar（`kSlowRowsPerS = 15000`），结论翻转。差别只在**表页是否已在 OS page cache**（表 28.8 GB）。另有一项佐证：本次 RAM 补集 36.93 GiB 的拷贝只花 **9 s**（10-10 那次 107 / 130 s），说明整机文件缓存是热的。

=> **`--ple-io` 的实际模式在同一份配置下不具确定性**，随 page cache 冷热在 `direct` / `mmap` 之间摆动。

**对 §2 W29 车设计的修正（重要）**：

1. **两臂都必须显式钉死**：A = `--ple-io mmap`，B = `--ple-io direct`。**禁止**用"不传 `--ple-io`（吃自动）"当臂 ---- 臂身份不固定，归因失效。
2. 判据加一条：每 run 记录启动段的 `PLE direct read probe` 行，作为**臂身份核验**。
3. 附带推论：本次重启后生产**已站在 `direct` 臂上**（未改任何配置），可作为"direct 长期稳态"的观察起点（看后续 prompt tok/s 与 `#1984` 特征串）。
