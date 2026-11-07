# W765 参数落地审计：裁决与修正（W764 的独立审计 + 我的复核）

触发：机主「**审计。还有是否全部落生产容器了，固化的有效参数。**」

## 0 两层的分工

- **我方（本会话）**：取三面 + 时间线 + md5，出 `W764_PARAM_LANDING_AUDIT.md`。
- **独立子 agent**（`auditor-w764`，只读、对抗立场）：
  `P0=0 / P1=0 / P2=4 / UNVERIFIABLE=6`，一句话结论 = **本轮声称属实，26 行 ADOPTED 全部有落点，
  P43 确已进入引擎进程运行态（不是脚本自报）**。
- **我对它的 4 条 P2 逐条独立复核**（不采信转述）。

## 1 审计的正面结论（两层一致）

| 项 | 证据 |
|---|---|
| **P43 三面全中** | 面 C（config args 尾部含 `--mtp-window 8192`）· **面 A（引擎进程 cmdline：`/proc/12: ... --vision --mtp-window 8192`）** · 面 B（引擎 environ 含 `HSA_OVERRIDE_GFX_VERSION=9.0.6` / `STRATA_PREFILL_CPU_SHARE=0`） |
| **源码语义真生效** | `generate.cpp:1801` 解析 -> `o.mtp_window`；`:3989/:3994` 传入 `mtp.load(...,o.mtp_window)`；`mtp.cpp:331/358/359/819/1143` **确有使用**（`window>0 && window<max_cells`，8192<262144 满足）=> 非"只解析不生效" |
| **本机源码 == 容器源码** | `generate.cpp` md5 `8a36f319...`、`mtp.cpp` md5 `1483883a...` 两侧一致 |
| **26 行逐项有落点** | 17 CLI（config args 且进了引擎 argv）· 2 ENV（config env 段**且**引擎 environ）· 4 CFG（visionx3 + backend）· 1 PATCH（覆写文件 md5 与留档一致）· 2 TOOL（工具件实存） |
| **md5 三处一致** | config 本机=166宿主=容器内 `6261ddf8a81b...`；register 本机=宿主 `881808e08c6d...`（本轮修后 `1416b467c2fd...`）；引擎二进制 `160611838796...` |
| **时序正确** | config mtime `02:41:52` -> 容器 StartedAt `02:41:59` -> 引擎 started `02:42:01` |
| **反向干净** | 引擎 argv = config args，**无"容器有、账上没有"的可调项**；引擎 environ 的 `STRATA_*` 只有已登记的 `STRATA_PREFILL_CPU_SHARE` |

## 2 四条 P2：逐条复核与裁决

| # | 子 agent 报的 | 我的复核 | 裁决 |
|---|---|---|---|
| **1** | `verify_config.py:2` docstring 写"证明...**真的**在 166 上生效"，但判定面**不读 `/proc/*/cmdline` 与 `/proc/*/environ`** => "生效"强于方法 | **成立**。我读源码确认：判定面 = config JSON / `Config.Cmd` / `Config.Env` / serve 打印的 `engine started` 行 / SETUP_KEYS / PATCH md5；确无 `/proc` 面 | **P2，已改**（在 docstring 里补了"判据面的边界"一段，明确结论强度分档） |
| **2** | `W764_PARAM_LANDING_AUDIT.md:50` 把 P11/P23（ENV）落点记为"config JSON 的 env 段"，**三面里没有"进程 environ"面** | **成立**。我做的三面是 A=serve cmdline / B=引擎 cmdline / C=config，**确实漏了引擎进程的 environ**（ENV 类参数该核这一面）。子 agent 已替我补齐（`/proc/12/environ` 两值都在） | **P2，已补齐**（本节 §1 的正面结论已含 environ 面） |
| **3** | `PARAM_REGISTER.tsv:42`（B00）证据栏写 `name="Radeon Instinct MI50 16GB"`，而运行期是 **32GB** | **成立**。这是 **W734 修了 `name()` 之后没同步的证据栏**（旧值遗留） | **P2，已改**（`16GB -> 32GB`）。**另**：我扫全表还发现 `X00` 也含 4 个 `16GB`，但**逐个看上下文后判定不改** ---- 那是**叙事性的**（"它写 16GB 而本卡是 32GB"、"真 16GB 卡不受影响"），是历史事实的记述 |
| **4** | 备份链最后一版 = `bak_w738_20261010_003916`（00:39）；`P43/P40` 在**所有备份里 0 命中** => "P43 由 CANDIDATE->ADOPTED"无法从备份复原 | **成立，且我把严重度从 P2 升为 P1**：这不是措辞问题，而是**明确的铁律违反** ---- `MEMORY.md §1` 写着「**改既有长件前先备份该件**」，而我从 **W739 起改 register 一次都没备份**（W739/W740/W745/W746/W760/W762/W763 全部裸改） | **P1，已补**：本轮改 register **先备份**（`bak_w765_20261010_025812`），并把 `verify_config.py` 也备份了 |

## 3 修正清单

| 项 | 动作 | 结果 |
|---|---|---|
| B00 证据栏 | `MI50 16GB -> MI50 32GB` | register `881808e08c6d...` -> **`1416b467c2fd...`**，两侧一致 |
| `verify_config.py` | docstring 补「判据面的边界」（+673 B） | **语法门 OK**，`md5 297d7c802d73`（另留 `.bak_w765b_*`） |
| 备份纪律 | 恢复"改前先备份" | `PARAM_REGISTER.tsv.bak_w765_*` x3 · `verify_config.py.bak_w765{,b}_*` x3 |
| 复核 | 改后重跑 | 核验器 **PASS=26 FAIL=0**；B00 `含 16GB=False / 含 32GB=True` |

## 4 无法验证清单（子 agent 的 6 项，我认同）

1. **P43 的收益 +3.39%** ---- 只读约束下不能复跑 6 臂；已核原始读数件与报告表一致，但 **n=2/臂、B 臂内差 3.0%、只测 64K** => 收益真值不可证（`W760 §6` 自认）。
2. register P43 证据里"生产日志 82k/92k 长会话 36.4-37.8 tok/s" ---- 现役容器刚重启，`requests_kept: 0`，日志相关行 0 命中 => 无法复核。
3. 引擎内部 `window_` 运行期被读到的**具体数值** ---- 未插桩；证到的是"argv 传入 + 源码会用 + 条件满足"。
4. P24（calibrate 929s）/ P38（59 ELF / 1,926,163 指令普查）的原始跑批 ---- 不在只读可复核范围，只确认工具文件存在。
5. P43 采纳后 warm 期答案分歧是否纯属会话态效应 ---- 采信 W760 §4 自述。
6. W746~W763 各波次 **缺快照** ---- 承发现 #4（未备份），无法确定这些行加入/改状态的确切时刻。

## 5 结论

**机主问的两件事，答案是：**
1. **「是否全部落生产容器了」= 是。** 26 行 ADOPTED（= 固化的有效参数）**逐项都有落点**，且本轮新采纳的 `--mtp-window 8192` 有**运行期证据**（引擎进程 cmdline + config + 时序三者自洽）。
2. **「审计」= 两层都做了**：`P0=0`；查出 **4 条 P2 + 我把其中 1 条升为 P1**（备份纪律），**全部已修**。

**唯一要长期记住的一条**：**改 register 必须像改 MEMORY.md 一样先备份** ---- 这条铁律早就写在 `MEMORY.md §1`，
我这次连续 7 个波次都在裸改。已恢复，并留下 30 份备份链。
