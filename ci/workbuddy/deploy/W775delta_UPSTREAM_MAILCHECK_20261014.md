# W775delta · 上游邮件与提交现状对照（2026-10-14）

> **触发**：机主令「看一下上游和 QQ 邮箱里 niko 的邮件，确认一下我们提交内容的情况，与我们这边的情况做比对」。
> **取证**：QQ 邮箱 API（inbox；Niko = `notifications@github.com`）· GitHub API（`Niko1221/Strata`）· 本机账本（`W750_MASTER_PLAN.md` / `params/PARAM_REGISTER.tsv` / `.workbuddy/memory/MEMORY.md`）· 生产日志本机副本 `deploy/tmp/_audit5_ev/strata-huihui-ud-iq4_xs.log`（3,771 行）。
> **时点**：上游「3 天批量清理」最近一次执行 = **2026-10-13T22:01-22:07Z**；本次复核 = 2026-10-14。
> **口径**：结论分三档 —— **实测**（原始日志/API 响应）· **源码**（读了源文件）· **推测**（显式标注）。

---

## §A Niko 的邮件（inbox 可见 20 条中 18 条来自该通知地址）

三批，按时间：

**批次 1 · 2026-10-13T22:01-22:07Z（10 封，**全部未读**）—— 上游批量清理**
逐字模板（三句，两次出现）：

> Thanks for the report. To keep the tracker current we are closing issues older than three days: 0.1.44 is out with a long list of fixes, and many older reports are covered by it or by 0.1.43.1.
> If this still happens on 0.1.44, please leave a comment here with your engine log (and the version line it prints), and we will reopen it. A new issue that links this one works too.

命中（每条 2 封 = 评论 + 关单事件）：**#1735 · #1734 · #1670 · #1595 · #1479**。

**批次 2 · 2026-10-10T16:18-16:34Z（8 封）—— 0.1.42 的合入与回复**

- `#1731` / `#1732` / `#1733`：**`in v0.1.42 with your authorship`**（三条均逐字保留署名）
- `#1595`：Niko 逐字确认**我们的表**促成 0.1.42 的默认行为改变（`the default share is not armed when the expert cache holds every expert`）
- `#1729`：Niko 逐字 `Thank you for the detailed log analysis, the GPU power and the split by session were exactly what we needed to look at.`
- `#1479`：Niko 逐字 `Added as HIP opt-ins (your patch, you are credited as co-author)`

**批次 3 · 更早**

- `#1396`：2026-10-08T12:18Z，`in 0.1.41 with your authorship kept`
- `#1729`：**2026-10-11T03:42:44Z 由报告人 `Simonqujian78` 自行关为 `completed`**（不是维护者关的）

---

## §B 我们提交内容的现状（本机账本 vs 上游实读）

| 条目 | 类型 | 我方角色 | 账本原记 | 上游 2026-10-14 实读 | 判定 |
|---|---|---|---|---|---|
| **#1396** | PR | 我们提 | 已 ported 0.1.41 | closed（10-08T12:18Z，`your authorship kept`） | 一致 |
| **#1731** | PR | 我们提 | 已合入 0.1.42 | closed（10-10T16:32Z，`in v0.1.42 with your authorship`） | 一致 |
| **#1732** | PR | 我们提 | 已合入 0.1.42 | closed（10-10T16:32Z，同上） | 一致 |
| **#1733** | PR | 我们提 | 已合入 0.1.42 | closed（10-10T16:33Z，同上） | 一致 |
| **#1855** | PR | 我们提（bench） | open | **open** · `mergeable_state=clean` · **0 评论 / 0 review** · base `fb58e0d`（**0.1.42 期**） | 一致，但已陈旧（4 天、跨 4 个版本无动静） |
| **#1877** | PR | 我们提（monitor FRU 容量一致性） | open | **open** · `clean` · **0 评论** · base `61b3fb5` | 一致，**但其对应 issue #1735 已被关单** |
| **#1734** | issue | 我们提 | **open**（我方已声明 no action needed） | **closed / `not_planned`**（Niko，10-13T22:06:46Z，批量清理） | **账本过期** |
| **#1735** | issue | 我们提 | **open** | **closed / `not_planned`**（Niko，10-13T22:06:50Z，批量清理） | **账本过期** |
| **#1926** | issue | 我们提（4 条文档级 notes） | open / 0 评论 | **open / 0 评论**（无上游回复） | 一致，**待回音** |
| **#1923** | issue | 我们提（专家缓存淘汰策略） | open / 2 评论均我方 | **open / 2 评论均我方**（无上游回复） | 一致，**待回音** |
| **#1670** | issue | 他人提，我们 3 条评论**已删** | 不再跟 | **closed / `not_planned`**（10-13T22:05:44Z） | 账本未记结局 |
| **#1595** | issue | 他人提，我们贡献促成修复 | 我方赢（修入 0.1.42） | **closed / `not_planned`**（10-13T22:03:49Z，**尽管 10-10 已确认修复并入 0.1.42**） | 账本未记已闭 |
| **#1479** | issue | 他人提，Niko 逐字判我方 patch、co-author | co-author | **closed / `not_planned`**（10-13T22:01:03Z） | 账本未记已闭 |
| **#1729** | issue | 他人提，我们贡献 | 已改短版回帖 | **closed / `completed`**（10-11T03:42:44Z，**报告人自关**） | 账本未记已闭 |

**读法（重要）**：`not_planned` 在这批里**不等于"被否决"** —— 它是「**超过 3 天没动 + 0.1.44 已发**」的清理口径。#1595 就是反例：修复明明已进 0.1.42，仍被关成 `not_planned`。所以 **#1734 / #1735 的关单不能读成"上游否了我们的建议"**，只能读成"跟踪器到期清理"。

---

## §C 版本面

| 项 | 值 |
|---|---|
| 我们在跑 | **0.1.42**（镜像 `strata-gfx906:0.1.42`；生产 config md5 `ff8cb973...`） |
| 上游已发 | **0.1.43**（10-11T14:40Z）· **0.1.43.1**（10-12T17:30Z）· **0.1.44**（10-13T19:26Z）· **0.1.44.1**（10-14T00:13Z，官方推荐用这一版） |

即 **4 天 4 个版本**。账本 `MEMORY.md` 第 2 行「上游 Niko1221/Strata @v0.1.42」措辞会被误读为"上游最新"，已按此改注。

---

## §D 与我们现有工作直接对应的上游新条目（0.1.43 - 0.1.44.1）

| # | 上游条目（逐字摘） | 对应我们的项 | 判断 |
|---|---|---|---|
| D1 | 0.1.44 为 Unsloth 文件写入 `STRATA_ROUTE_TAIL_SKIP=0` **where every expert is in RAM**（skip 在那里反而改答案 KL 0.056 -> 0.086，换 +4-10% 速度）；**RAM-budget 模式保留 skip（+26-67%）** | **`P57` 更正**（`ROUTE_TAIL_SKIP` 判错） | **需判定我们落哪一侧**：我们是「VRAM 9761 槽 + RAM 补集 36.8 GiB + SSD 层」，**不是**"全部在 RAM"，也**不是** RAM-budget 模式（`--resident-budget-gib` 已废） |
| D2 | `STRATA_PIN_BY_NEED=1`（Windows/WDDM、CUDA 与 HIP）把 GPU 放不下的专家注册为 pinned memory，**并为自适应层换出的专家加了第二档**（5070：prompt 读 +4.4%，5/5 pairs） | **B7 `--resident-experts` / 借区** | 上游在替我们这条路的"RAM 侧 pin 策略"做优化；我们是 Linux+HIP，**适用性待核**（上游那句把 Windows 点得很明，但括号写了 CUDA 与 HIP） |
| D3 | **Foresight exchanges keep the experts they move（#2134）** | **`P70`（`FS_SLOTS` / Foresight）** | 上游修了 Foresight 的**丢专家 bug**；我们判 `P70` 用的是 0.1.42 观测 => **该判定所依据的观测可能被此 bug 污染**，至少须加限定条件 |
| D4 | **Windows AMD cards: name, VRAM and driver from the registry（#1587）** | **我们的 #1735 / PR #1877** | 同类问题的**Windows 侧**在 0.1.44 修了（#1587）；我们的 **Linux 侧**被批量关单、PR 仍 open。即：**问题类别上游认，平台不同** |
| D5 | 0.1.44 setup 规则：`Where the experts fit in RAM with 16 GiB to spare, setup keeps every expert in RAM`（对旧 budget 规则：decode x1.34-1.40、4K prompt x2.07） | **`P09` `--resident-budget-gib`**（已废，`[EXT: 小 RAM 预算]`） | 上游在 RAM 预算判定上换了规则并给了量级；我们已走 `--resident-experts` 路线，**方向一致** |
| D6 | 0.1.43 的 AMD 提速（`ROUTE_TAIL_SKIP` 默认、measured PCIe share、fused prompt kernels、16K chunk）**逐字限定在 RDNA4（gfx1200/gfx1201）**，且 `RDNA3 (gfx11) and older keep their 0.1.42 behaviour` | 全部 gfx906 相关工作 | **0.1.43 的 AMD 增益不覆盖我们**（上游自己写死）。升版动机只能来自通用修复，不能来自 AMD 提速 |
| D7 | `--adapt-async 1` 也可用于 arena 模式；`STRATA_ARENA_PIN_GIB`、`STRATA_PCIE_MIN1` | 我们已测过的 `--adapt-*` 族 | 上游把 async 自适应扩到 arena 模式；我们是 RAM 驻留模式，**待核** |

---

## §E 本次比对新发现的账实不符（**P0**）

### E1 账本称「PLE 表未加载 / 探针不可达 / 该路径从不执行」—— **直接被生产日志推翻**

账本原文（三处，措辞一致）：

- `W774_UPSTREAM_0142.md` §7.5：「生产 config `args` 无 `--ple-io` 亦无 `--ple-gguf` => PLE/n-gram 表**未启用** => 探针代码路径从不执行。**生产日志无任何 `PLE ... rows/s` 行，与之一致。**」
- `W750_MASTER_PLAN.md` §0.5.3 同义展开；`W775delta_REL0142_LEDGER.md` S-16 记「已核不可达」；`W775delta_EXT_VALUE_REGISTER.md` P58 同义。

生产日志（本机副本，serve 路径）**实读**：

```
L2714  [strata] 2026-10-10 18:27:01 engine started: /src/build-906/strata --serve --pack /data/packs/huihui-ud-iq4_xs ...
L2720  strata generate: --ple-io direct measures slow here (14560 rows/s, about 60 MB/s of random 4 KiB reads):
                        using --ple-io mmap instead (the OS file cache holds the pages; ...)
L2722  strata generate: PLE on, table 320001536 rows of /models/huihui-ai/.../Qwen3.8-Flash-Next-UD-IQ4_XS-00002-of-00003.gguf
```

计数（整份 3,771 行）：**`PLE on, table 320001536 rows` 出现 38 次**；**`--ple-io direct measures slow here` 出现 2 次**（**14,560** 与 **13,268** rows/s）。

->  **PLE 表是加载的、探针是执行的、生产 `--ple-io` 已被自动切成 `mmap`**。
**根因**：原判用的 grep 模式是 `PLE ... rows/s`（行首其实是 `--ple-io`，且 `rows/s` 在行中），**过窄** => 空结果被读成"路径不存在"。这也和同族另一处自相矛盾：`W715_HUIHUI_SWITCH.md` §4.1 明明记为「**PLE 表（n-gram 表）---- 本来就开着**」并引了同一行日志；`register P91`（`STRATA_PLE_IO=ram` = **-45% REJECTED**）本身也只有在 PLE 表真的加载时才有意义。

### E2 由此浮出一条**从未对照测过**的可能杠杆：`--ple-io direct`

上游 0.1.43.1 的两条修复正是我们这个形状（**逐字摘**）：

- **#2040**：`Its 15,000 rows/s bar was set on NVMe drives; a SATA SSD tops out at 10-14K rows/s with direct reads and the switch to mmap made its prompts about 7x slower (#2040: 77.8K-token prompt, 884 tok/s direct against 76-154 mapped).`
- **#1984**：`when the start-up check finds --ple-io direct slow, 0.1.42 switched to --ple-io mmap. A prompt's first chunk then read its n-gram rows as one page fault after another from a cold 27 GB table, with no progress mark, and the 60 s watchdog stopped the engine.` 现象：**长 prompt 停在 `layer 1 of the prompt chunk` 并重启引擎**。
- 0.1.43.1 的修法是 **part 1：检查只警告、不再自动切（保留 direct）**；part 2：给 mmap 模式加 4,096 行预读；part 3：watchdog 阈值按 10 s 窗判盘忙。

**我们的事实**（实测/只读核实）：

| 项 | 值 | 来源 |
|---|---|---|
| 166 磁盘 | `sda 953.9G **Fanxiang S100Pro**`，`ROTA=0`（SATA SSD），XFS on `/` | `lsblk` 实读 |
| 探针量到的 direct 吞吐 | **14,560 / 13,268 rows/s** | 生产日志 L2720 / L2776 |
| 上游所判的 bar | **15,000 rows/s**（"set on NVMe drives"） | 0.1.43.1 relnote |
| 上游所判的 SATA SSD 带 | 10-14K rows/s | 同上 |
| PLE 表规模 | `320,001,536 rows` x 90 B/row = **约 28.8 GB**（≈ 上游说的 "cold 27 GB table"） | 日志 + 0.1.42 help `--ple-row-cache N ... 90 B each` |
| 我们显式给过 `--ple-io` 吗 | **没有** => 落进"未显式给"分支 => 被自动切 | 生产 config `args` 实读 |

->  **我们正是上游判定为"误切"的那一类配置**（SATA SSD + 行速略低于 bar + 未显式指定）。而 `register` 只测过第三种臂（`STRATA_PLE_IO=ram`，-45% REJECTED），**`direct` 与 `mmap` 的对照从未做过**。

**量级待测，不作结论**。反方向的可能也存在：mmap 走 OS page cache，而本机 RAM 128.7 GiB、表仅 28.8 GB，**若表能长期驻留 page cache，mmap 未必慢**（上游那次是 32K/77.8K 冷起点）。本机日志 L2727 又显示文件层与 55.4 GiB 的 RAM 补集在抢 file cache，所以"能否常驻"本身就是要测的量。

**潜在影响面（须留意，不必现在改结论）**：W28/W28E 的冷路径归因（「冷读主因 = budget 关借区/借区无 RAM 副本」）**未把 `--ple-io` 臂列为变量**；若 PLE 表读与专家 blob 读混在同一个"冷读"口径里，该归因至少不完整。当前日志 `layer 1 of the prompt chunk` 命中 **0 次**，但该日志只覆盖两次引擎启动，**不足以排除** #1984。

---

## §F 本次已落地的更正（改动前备份 `deploy/tmp/_upchk_bak/`）

| 文件 | 改动 |
|---|---|
| `W774_UPSTREAM_0142.md` §7.5 | PLE 行结论作废 + 换成本次实读证据 |
| `W750_MASTER_PLAN.md` §0.5.3 | 同上；**撤回「该待办关闭」**，改开 `--ple-io direct` 对照车 |
| `W750_MASTER_PLAN.md` §0 上游行 | 补 #1734/#1735 等 5 项关单结局 + 上游版本 0.1.44.1 |
| `W750_MASTER_PLAN.md` §0 P3/W11 行 | 同上；补 #1923/#1926 仍 open |
| `W750_MASTER_PLAN.md` W13-补 行 | `#1923` 评论数 1 -> 2（均我方） |
| `W775delta_REL0142_LEDGER.md` S-16 | 「已核不可达」作废；待办撤回重开 |
| `W775delta_EXT_VALUE_REGISTER.md` P58 | 中间列改为"本机正是该情形的实际使用者" |

**未动**：参数值（register status 未动）· 生产 config · 上游（本次无任何写操作）。`W18`/`W21` 等无关件未触碰。

---

## §G 待机主定 / 建议

| 序 | 事项 | 我的建议 |
|---|---|---|
| G1 | **#1923 / #1926 是否跟进** | **时间敏感**：上游的清理规则是">3 天未动即关"，#1923/#1926 生于 10-11，**今天起就进入被清理窗口**。要么允许我发一条简短的"仍适用/请保留"式跟踪评论，要么接受它们被同上批关掉（内容仍在，可随时新开链接） |
| G2 | **PR #1855 / #1877 是否催** | **不建议催**。上游 open PR 队列 20+，两条均 `clean` 无冲突；#1877 的对应 issue 已被清理，但这不影响 PR 本身进入评审 |
| G3 | **`--ple-io direct` 对照车（E2）** | **建议做**。0.1.42 已内置该开关，**不必升版**；一个临时实例、单变量、长短两档即可判定。这是本次比对里唯一"可能直接改善生产"的项 |
| G4 | **0.1.43 - 0.1.44.1 逐条台账** | 建议做（我们已有 `W775delta_REL0142_LEDGER.md` 的体例）。但**升版动机要单独论证**：D6 已排除 AMD 提速，剩下的是 D2/D3/D4 这类通用修复与 `#1984` 稳定性修复 |
| G5 | **是否重提 #1735（Linux FRU）** | 暂不提。同类问题上游在 Windows 侧刚修（#1587），说明类别被认；我们已有 PR #1877 在队列里，重开 issue 只会再被 3 天规则扫一次 |

---

## §H 取证命令与落盘物

- 邮件：`mcp__qq-mail__SearchMessages(q="Niko")` / `ListMessages(dir=inbox)`
- 上游：`GET /repos/Niko1221/Strata/{releases,issues,pulls,search/issues,issues/N/events}`
- 本机复算脚本：`deploy/tmp/_up_probe.py`（提交面）· `_up_detail.py`（发布说明 + 四条 thread）· `_up_pr.py`（PR 详情 + 全仓提及）· `_up_thr2.py`（#1479/#1595/#1729 角色）
- 原始落盘：`deploy/tmp/_rel_v0_1_43.md` · `_rel_v0_1_43_1.md` · `_rel_v0_1_44.md` · `_rel_v0_1_44_1.md` · `_up_probe.out.txt` · `_up_detail.out.txt` · `_up_pr.out.txt` · `_up_thr2.out.txt`
- 生产日志本机副本：`deploy/tmp/_audit5_ev/strata-huihui-ud-iq4_xs.log`（AUDIT5 拉回，3,771 行）
