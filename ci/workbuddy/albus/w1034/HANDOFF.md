# W1034 交接件 · Strata（gfx906 / MI50）项目

> SNAPSHOT: round=W1046 date=2026-11-07 prod_exe=strata-0.1.57-attn prod_md5=3b758f88ddad25cdad236be267810a9e config_md5=3dde880125925d785a49da69fa1ebdfb container=2d765942e041 image=strata-gfx906:0.2.11-101 branch=e181bda5 tag=mi50-0.2.11-r33-14 picks=209d3ca2
>
> 可粘贴提示词的**唯一副本**：`albus/w1034/HANDOFF_PROMPT.md`（≤3000 字符）。完整交接件是本文件。机器自证门：`tools/handoff_check.py`。
> 本件**不同步 166**：它描述的是本机文档、门脚本与迁移操作；166 只保存六件权威件的现场副本。

---

## 0 结论先行：为什么交接不能只靠「新会话会记得」

本轮上网核了 WorkBuddy 官方文档，最关键的一句在「新建任务栏」：

> **「每个对话对应一个独立任务，任务之间互不影响，各自维护独立的工作空间与上下文。」**
> —— `https://www.workbuddy.cn/docs/workbuddy/From-Beginner-to-Expert-Guide/Function-Description/Task-Bar`

也就是说：**新会话不会自动继承这段对话的任何内容**。能跨会话保留的只有两块——① 同一个工作空间里的文件；② 环境自动注入的记忆（见 §2，按观察到的行为算，不能当官方承诺）。所以交接做成三件互相校验的东西：

| 件 | 作用 | 新会话怎么用 |
|---|---|---|
| `albus/w1034/HANDOFF_PROMPT.md` | 短提示词，自包含到能独立启动 | 粘贴发送；或 `@` 引用；或 `/strata-handoff` |
| `albus/w1034/HANDOFF.md`（本件） | 状态、铁律、门、未结、证据出处 | 提示词第 1 步要求先读 |
| `tools/handoff_check.py` | 机械自证：文件在、门齐、现值自洽、提示词没腐坏 | `python tools/handoff_check.py` |

**证据等级**（本件所有结论按此标注）：`官方核实` = 本轮 WebFetch/WebSearch 逐字核过；`会话观察` = 本会话系统层确实注入了，但官方文档未记载；`本机实测` = 工作区文件 / 166 现场取值。

---

## 1 机主的迁移操作（5 步）

1. 在左侧**同一空间分组**上点「新建任务」（`官方核实`：Task-Management 「如需在当前工作空间中开展另一项工作…点击**新建任务**」）。旧会话**归档**即可，不要删除 —— 官方写明「删除后…无法恢复」。
2. **工作空间手动选 `D:\workbuddy_space\strata_ws`**（`官方核实`：Create-Task「选择工作空间…WorkBuddy 会基于该目录读取和处理文件」；Task-Bar「若未提前指定，WorkBuddy 会在新建任务时自动创建独立空间」）。**这一步最容易漏**：选错就得到一个空目录，所有权威件都看不见。
3. 模式保持**默认 Agent**（`官方核实`：Task-Bar「默认即为 Agent 模式」，Plan / Ask 在输入框 `+` 菜单里，互斥）。
4. 粘贴 `HANDOFF_PROMPT.md` 全文发送（长度 <3000 字符，不会被输入框自动收起成折叠条目 —— `官方核实`：Task-Bar「粘贴超过 3000 字符的文本时…自动收起」）；也可直接输入 `/strata-handoff`，或用 `@albus/w1034/HANDOFF_PROMPT.md`。
5. 等它回报「交接自证 + 现行队列 + 生产健康」。**若 `HANDOFF: FAIL`，先让它修交接，别下新任务指令。**

> 本机工作区**不是 git 仓库**（`本机实测`：`git status` 报 `not a git repository`）。主线 git 在 166 的 `~/strata166/pr/strata-fork`。别在本机跑 git 操作指望它管文档版本。

---

## 2 新会话「自动」能拿到什么

| 内容 | 会不会自动有 | 依据 / 处理 |
|---|---|---|
| 本轮对话历史、工具输出、推导过程 | **不会** | `官方核实`：任务间独立上下文 |
| 工作区文件（deploy / albus / tools / .workbuddy） | 会，但**前提是选对工作空间** | `官方核实`：Create-Task / Task-Bar |
| 用户级长期记忆（助手名 Albus、机主偏好、本机工具坑） | 本会话确实被注入 | `会话观察`；提示词内仍重述了致命项，不依赖它 |
| 工作区 `MEMORY.md`（2890 字符，窗口 ≤3000） | 本会话确实被注入 | `会话观察` + `本机实测`；详细版在 `MEMORY_DETAIL.md`（544 KB，需主动读） |
| 每日日志 `.workbuddy/memory/2026-11-07.md` | **不会**自动注入 | `会话观察`；要主动读，append-only |
| 技能清单 / 连接器清单 | 本会话确实被注入 | `会话观察`；不在官方文档中核到专门页面 |
| 166 生产现场状态（引擎 md5、/health、VRAM） | **不会** | 每次只读现场取；`handoff_check.py --live` 可代劳 |
| 跨会话的某次具体讨论 | 不会 | 用 `conversation_search`（服务端检索历史对话） |

`官方未核到`：WorkBuddy 官方文档里没有专门讲「记忆文件自动注入」的页面（站内检索无结果）。因此**提示词按最坏情况写死自包含**，不赌注入。

---

## 3 状态快照（2026-11-07 02:1x，`本机实测` / 166 现场只读）

| 项 | 值 |
|---|---|
| 容器 / 镜像 | `2d765942e041`（full `2d765942e041f31f7cf3999a7fbabe8073a0ca0fd21b355228392c1624150a04`）· `strata-gfx906:0.2.11-101` |
| 在产引擎 | `strata-0.1.57-b12180` · md5 `d24f8293b575fbcee6c097239d9599cb` · 43,207,464 B（llama.cpp b12180 == master bcb01528 + mmq@4c1004c）；回滚 `k10p` / `-001` |
| config | md5 `53ac61e0c663a6a46b7a5aa2e610bf43` · `exe=/data/bin/strata-0.1.57-001` · args 37 / env 9 |
| 健康 | `/health` ok（max_context 262144）· `restarts=0` · `StartedAt=2026-11-06T16:48:17Z` |
| 显存 | VRAM used 33,606,098,944 B / total 34,342,961,152 B（free ≈0.69 GiB）；expert cache 6779 槽，prompt 借 1554 槽 |
| 回滚件 | `-001`（在产）· `-002/003` · `-004`(0.9.0) · `-005`(H1) · `-006`(H2) · `-008`(ladder-5) · `-009`(K10) · `-010`(K10 复测) · `-011`(K13)；`ci/rollback.sh --exe strata-0.1.57-001 --apply` |
| 主线 | `gfx906/mi50` @ `e181bda5`（`mi50-0.2.11-r33-14-2-ge181bda5`）· 领先 80 / 落后 0 · **脏 0 行**（在 166 上）；实验分支 `gfx906/port-all` @ `8b44f3d1`（领先 2） |
| 实验分支 | `gfx906/lcpp-picks` @ `209d3ca2` |
| 分母 | **现场跑 `python tools/progress.py`**；本件写成文字会漂移，§0.1 是唯一现值 |
| 队列 | **只读 `W832_OPT_PLAN_V2.md §0.1`**：`R51` → `R95` → `R94` → `R91` → `R89` → `R46` → `R49` → `R50` |
| 残留 | `qq_*` 容器 0 个；W1033 生产 0 次重启 / 0 分钟停机 |

**上一轮（W1033）净结果**：整改 64 份审计输出、方案单源化、撤回 AUDIT26 对上游 PR 的一处外网误判；生产零改动。

---

## 4 权威件地图（`W832 §0.2` 是导航唯一入口）

| 文件 | 角色 | 改它的规矩 |
|---|---|---|
| `deploy/W832_OPT_PLAN_V2.md` | **唯一**调优方案；§0.1 唯一现值、§0.2 导航、§6.5.0 回写块目录 | 分母 / 队列只改 §0.1；其余章节的数字必须带轮次或标历史快照 |
| `deploy/PROGRESS.tsv` | **唯一**结论账与分母 | 每轮加行；`tools/progress.py` 派生分母；`audit_scope.py §D` 拦手写 |
| `deploy/params/PARAM_REGISTER.tsv` | **唯一**参数册 | 改参**唯一入口**：register → `gen_config --write` → 推 166 → restart |
| `deploy/AUDIT_INDEX.md` | 23 件编号审计 + 39 件派生产物清单 | P 列由 `audit_outputs.py` 逐件比对 `> VERDICT:`；合计由 `audit_index.py --fix-total` 派生 |
| `deploy/ID_MAP.tsv` / 最新审计件 | 编号映射 / 最新审计 | `mirror_check.py` 动态派生「最新审计件」，别再写死 |
| `deploy/SESSION_STATE.md` | 现状一页纸 | **不自持队列**（§9 已标为历史快照） |
| `.workbuddy/memory/MEMORY.md` | 项目长期记忆（≤3000 字符窗口） | **禁 Edit 逐条改**；改本件走 `mem_slim.py`，先归档 `MEMORY_DETAIL.md` |
| `albus/wXXXX/reply.md` | 每轮四件套报告 | 由 `round_close.py --post` 生成 POST 校验头；历史报告是当时快照 |

**六件权威件**改完必须 `python albus/w1003/mirror_check.py --sync` 逐字节同步到 166（AUDIT27 修过「最新审计件写死」的盲区）。

---

## 5 铁律全表

**A. 生产（违反过，代价最大）**
1. 任何停生产 / 重启 / 装引擎 / 独占 GPU 的动作：**先一条消息写明停机时长，等机主点头**。W1031 未等答复就停了 16 分钟，`P392` 的数值门至今因此挂着。
2. 166 **只能断电冷启**，禁 `systemctl reboot`（W1031 用过，被纠正）。
3. 装机前断言「只有一个引擎持卡」；两个引擎同时持卡 → GPU 卡死、dmesg userptr 失败链、`rocm-smi` hang（`P386`/`P387`）。
4. 远端脚本用 `setsid nohup` 托管、`trap` 必回滚；ssh 被本地 timeout 杀掉时远端 trap 不会执行过（这是 ladder-5 事故的起点）。
5. 换二进制 `cp -> .new + mv`；容器内文件一律 `docker exec`；编译在镜像内做；一次到位，禁分批跳版。

**B. 改参与测量**
6. 改参唯一道（见 §4）；`verify` **只判配置面**，运行期结论必须取引擎。
7. A/B 自比：同形状 / ms-per-step / 排冷热 / 含 adapt+join / A-B 交错；判据 **2× 当次 CV**，相位只用来定位不作结论；重启丢前 2 个请求。
8. 长提示的**逐字节贪心指纹不可重复**（`P388`：同一引擎 `en2k` 234 vs 242、`zh2k` 82 vs 79）——禁止再拿它当数值门。数值面用 teacher-forced top-1 / KL，或 prefill-only LOGPOS 探针。
9. 「K10 免费」**只在 prefill 2K/8K 形状成立**，不可外推到任意形状（`P392`）。

**C. 文档与账本**
10. 单源化：现值只在 §0.1；队列只在 §0.1；历史排期必须带日期标记；活文档**禁写 `W832:<行号>`**（改小节名）。
11. 撤回结论必须**追到所有下游**（审计件 → 索引 → 方案 → 账本 → 门 → 报告），AUDIT28 的 P0 就是漏了这条。
12. 冻结历史件（`W986_PLAN_V3.md`、`AUDIT_LEDGER.tsv`、记忆件）**只登记不逐字重写**（W1007 改完再回滚的教训）。
13. **写文件禁同一表达式内 read + open**：W1033 一次 `io.open(p,"w").write(re.sub(...))` 先截断后抛错，把 AUDIT24 写成 0 字节，靠 `*.bak_a28_20261107_015655` 才恢复。改长件先备份。
14. 每轮收工四件套 + 账本行 + 全套门 + 当日记忆 append-only（见 §6）。

**D. 本机工具坑（`用户级长期记忆`，本机实测）**
15. 压缩包一律 `D:\Program Files\7-Zip`，先看 `7z l` 列表再解。
16. Bash shim：路径用**正斜杠 + 引号**（反斜杠会被吞）；argv 8191 上限，长 payload 走 stdin + base64；URL 型参数加 `MSYS_NO_PATHCONV=1`；**不要 `2>/dev/null`**（traceback 走 stderr）；管道 rc 取 `${PIPESTATUS[0]}`；`dirname/cd/head/tail/ls/wc/grep/cat/cp/sleep/base64` 等不可用，用绝对路径 + Python/PowerShell 或专用工具。
17. 删除**只进回收站**（本机 `Remove-Item -Force` 实际进 `C:\$Recycle.Bin`；NAS 走 `SYNO.FileStation.Delete` API），**回收站由机主自己清**，不要追空间；`shutil.rmtree` / `os.remove` / `rm` / `Remove-Item` 一律禁。
18. 临时 `python -m http.server` 传完**立刻停**；`run_in_background` 任务会长期挂，kill 时会收到 failed 回执（曾残留一天，机主手机看到裸目录）。
19. **有技能必须用技能**（最高优先级）：涉及 `MEMORY.md` / 记忆件 / 压缩窗口，第一动作查技能清单并加载对应技能，fail-closed 执行，禁 Edit 挤牙膏。
20. 产物一律写 `albus/<主题或轮次>/` 专用子目录，根目录保持干净；**禁 `present_files` 及一切文件展示工具**，只在正文给路径清单。

**E. 沟通**
21. 极简、别反复问、别问上下文里已有的；「自主判断 / 自动执行 / 你定」= 把已列明的事直接做完；「从严」= 取最收紧档并把待办一并补上；「不要运行，先分析」= 只分析。
22. 人称反转：机主消息里的「我」= 助手，「你」= 机主自己；称呼用「你」，不要自作主张起昵称。
23. 严谨：数字标明**实测 / 源码核实 / 推测**；该上网查就查，核不到写「未复核」，不删也不当判据。

---

## 6 门清单（收工必须全绿）

`albus/w1002/round_close.py` 的 HARD（11 道）：`report_lint` · `report_depth` · `plan_lint` · `audit_index` · `plan_retired` · `pointer_lint` · `audit_scope` · `audit_outputs` · `plan_single_source` · `handoff_check` · `round_ledger`。

另有：`ci/prefill_phases/kernel_curve.py --check`、`ci/bundle_budget/bundle.py --check`、`albus/w1003/mirror_check.py --sync`、`tools/audit_closure.py`、以及 `round_close.py --post` 生成 POST 校验头。

- `audit_scope.py`：审计债 >8 轮 / 废止门以现行指令出现 / 缺报告 / 分母与队列漂移 → FAIL。
- `audit_outputs.py`：23 件编号审计的 `> VERDICT:` 与索引 P 列逐件比对，39 件派生产物必须在 `COMPANIONS:` 里。
- `plan_single_source.py`：唯一队列恰 1 行、§6.5.0 目录覆盖全部回写块、行号指针清零、分母自洽。
- `handoff_check.py`（新）：交接三件齐全、提示词 ≤3000 字符且含全部锚点、SNAPSHOT 可解析、门脚本齐全且自身在 HARD 里、最新报告存在；`--live` 只读核 166；`--self-test` 负向。
- `round_ledger.py`（W1035 新增）：从 SNAPSHOT `round=` 取当前轮次，要求 ① `albus/<round>/reply.md` 在且 ≥1500 字符 ② `PROGRESS.tsv` 至少一行 source 列 == 该轮 ③ 当日记忆提到该轮；`--self-test` 负向 3/3。起因：旧门只验「报告写得好不好」，不验「这一轮有没有落账」。

**每轮收工命令**：`python albus/w1002/round_close.py --report albus/wXXXX/reply.md --post`

---

## 7 未结与边界（别误读成「可以开跑」）

| 号 | 状态 | 解除条件 |
|---|---|---|
| `P392` | KL / 数值门**未完成**；`quant_quality` 的 K10 腿空转（12 GB 显存、64 W、10 min 无输出），已停并恢复生产 | 改用 **prefill-only LOGPOS** 探针（生产配置 + 单条 ~1000 token，不碰 short-read）；**需停生产 10–15 min，未经点头不执行** |
| `R51` | W1031 范围收窄重开；账本原题仍是 DONE_NEG | 先补 `P392` 数值门，再在 **2026-10-19 MMQ 栈上限**内做单点 A/B |
| `R101` | OPEN | 与 `P392` 的 top-1 / KL 一起合并判定 |
| `P309` / `P335` | OPEN，各有明确的容器级 / 观测面前提 | 见 `deploy/PROGRESS.tsv` 各行的 note |
| 其余约 50 条 OPEN | 多为历史候选或已判否但未清账 | **不是待办清单**；队列只认 §0.1 的 8 条 |

最近三轮的关键实测（`本机实测`，别丢）：`001` 532.76 / 714.89 tok/s；`K10`（0.9.0 树 + MMQ 头 @`4c1004c`，含 `#29953`/`#30168`/`#30553`）534.83 / 716.72 = **零代价**；`K13`（K10 + `#29948`）508.52 / 684.10 = **−4.9% / −4.6%**（8–19× CV）。⇒ **要上游修复就停在 2026-10-19 那一点，不要越过 `#29948`**。`AUDIT28` 另更正：`#31188` 的性能数字属实，但那是 CUDA + MoE 融合路径，gfx906 不适用（不是「无法核实」）。

---

## 8 举一反三：新会话最容易踩的 10 个坑

1. **没选工作空间** → 空目录里「找不到权威件」，然后开始凭印象编结论。
2. **把 §6.5 里带日期的重排快照当现行队列** → 做错条目（§0.2 就是为这个加的）。
3. **把历史报告里的分母 / 队列当现值** → 一律现场跑 `progress.py` + 读 §0.1。
4. **以为对话历史会自动继承** → 官方文档明确独立上下文；所有背景都在文件里。
5. **拿已废止的指纹门 / 退役数字当判据** → `plan_retired.py` 会拦，但别等门拦。
6. **看到「作者称 / 无法核实」就当结论** → 上 GitHub API 逐字核 PR 正文（AUDIT28 的 P0 就是漏了这一步）。
7. **停机、重启、独占 GPU 不问** → 先写停机时长等点头。
8. **`systemctl reboot` / 双引擎持卡** → 只能断电冷启；装前断言单引擎。
9. **同式 read+open / 不备份 / `present_files`** → 三条都踩过，见 §5 C/E。
10. **改 `MEMORY.md` 不用技能** → 最高优先级铁律，绕技能 = 绕过窗口判据。

---

## 9 保鲜规则（交接件自己怎么不腐坏）

- **提示词不写会漂移的数字**：分母、队列、时间戳都改成「现场取 / 以 §0.1 为准」。因此加账本行、换队列、过日期都不必改提示词。
- `SNAPSHOT` 行只放**稳定标识**（轮次、日期、引擎 / config md5、分支、容器、镜像）。生产换二进制后，新会话第一轮应更新它 —— `handoff_check.py --live` 会提示不一致。`round` 字段只在**该轮 `reply.md` 已写完**之后才改：先改会让 `handoff_check` 的 F 项 FAIL，这是有意的（交接不许指向一份不存在的报告）。
- `handoff_check.py` 已接进 `round_close.py` 的 HARD：**每轮收工都会验交接件**，文件缺失 / 提示词超长 / 锚点丢失 / 门不齐会直接 FAIL，逼着当场修，不会出现「交接件停在上个月」。
- 交接件**不同步 166**（理由见文件头）；权威件六件照旧 `--sync` 同步。
- 若换工作目录或换机器：改提示词第 1 行的路径、§1 第 2 步、`SNAPSHOT` 里的 md5/分支，并把 `tools/handoff_check.py` 的 `ROOT` 相对定位再跑一次 `--self-test`。

---

## 10 本轮外网核实记录（全部 `官方核实`，URL 可复查）

| 来源 | 核到的事实 | 用在交接哪里 |
|---|---|---|
| `workbuddy.cn/docs/workbuddy/From-Beginner-to-Expert-Guide/Function-Description/Task-Bar` | 「每个对话对应一个独立任务…各自维护独立的工作空间与上下文」；默认 Agent 模式；未指定路径会自动创建独立空间；粘贴 >3000 字符会收起；项目级 slash commands 在 `.codebuddy/commands/` | §0 §1 §2 §9 |
| `workbuddy.cn/docs/workbuddy/Create-Task` | 可「选择工作空间」，选定后基于该目录读写；`@` 引用文件 / 文档 / 规则；上传拖拽文件 | §1 §2（@ 引用通道） |
| `workbuddy.cn/docs/workbuddy/Task-Management` | 「在已有任务中继续发送消息…基于之前的上下文」；同空间分组可「新建任务」；删除任务「无法恢复」 | §1（同空间新建、归档而非删） |
| `workbuddy.cn/docs/workbuddy/Conversation` | 讲了回退 / 编辑 / 刷新 / 引用 / 上传，**没有**记载上下文压缩或会话迁移能力 | §2（不赌自动继承） |
| `codebuddy.cn/docs/cli/slash-commands` + `workbuddy.ai/docs/cli/slash-commands` | `.codebuddy/commands/*.md` → `/<文件名>`；YAML frontmatter 支持 `description` / `argument-hint` / `allowed-tools` / `model`；正文即 prompt；`$ARGUMENTS` / `$1` | `.codebuddy/commands/strata-handoff.md` 的格式依据 |
| `workbuddy.cn/docs/workbuddy/Overview` | 只有产品简介与建议阅读顺序，**没有**会话 / 记忆机制说明 | 标注「官方未核到记忆注入页面」 |

**未核到**：站内检索 `MEMORY.md` / 项目记忆自动注入的官方文档无结果 ⇒ 提示词按「不自动注入」写，§2 里相关行标 `会话观察`。

---

## 11 给新会话的一句话

**先读文件、先跑门、先自证，别凭印象续写；生产零改动是你的默认状态，任何会停机的动作先问。**
