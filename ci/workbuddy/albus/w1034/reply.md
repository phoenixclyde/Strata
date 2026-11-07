# W1034 报告 · 会话迁移交接：三件资产、一道自证门、以及「新会话到底会继承什么」的官方答案

**一、生产容器（10 字段）**

| # | 字段 | 值（全部容器内 / 现场取值，2026-11-07 02:1x 只读） |
|---|---|---|
| 1 | 容器 / 镜像 | **`2d765942e041`**（full `2d765942e041f31f7cf3999a7fbabe8073a0ca0fd21b355228392c1624150a04`）· `strata-gfx906:0.2.11-101` |
| 2 | 运行中引擎 | `strata-0.1.57-001` · md5 `5e63174dbd7cc04e5fa1b5fc455b2a73` · 42,947,088 B · `--version` = `strata 0.1.57` |
| 3 | config | md5 `53ac61e0c663a6a46b7a5aa2e610bf43` · `exe=/data/bin/strata-0.1.57-001` · args 37 / env 9 |
| 3a | args 明细（19 个 flag） | `--pack /data/packs/ud-q4_k_xl` `--native …UD-Q4_K_XL-00001-of-00004.gguf` `--expert-profile /src/data/expert-profile.bin` `--expert-cache auto` `--pcie-frac 0.20` `--spec 4` `--spec-min-p 0.70` `--mtp /data/mtp/rt` `--max-context 262144` `--kv k8v4` `--prefill auto:16384` `--prompt-cache-every 8192` `--expert-profile-save /data/profiles/q4kxl-learned.bin` `--conversation-cache-mib 4096` `--vision` `--mtp-window 8192` `--vram-reserve-mib 832` `--ple-io mmap` `--pool-workers 10` |
| 3b | env 明细（9 个） | `HSA_OVERRIDE_GFX_VERSION=9.0.6` `STRATA_PREFILL_CPU_SHARE=auto` `STRATA_PREFILL_CPU_SHARE_MAX=3072` `STRATA_ROCBLAS_TUNING=/data/gfx906-rocblas-5.7.0.txt` `STRATA_GFX906_TUNED=1` `STRATA_CKPT_MOVE_PARK=1` `STRATA_DECODE_TIMING=1` `STRATA_SPEC_DEPTH=1` `STRATA_PREFILL_TIMING=1` |
| 4 | 健康 | `/health` = `{"status":"ok","max_context":262144,…}` · `restarts=0` · `StartedAt=2026-11-06T16:48:17Z` |
| 5 | 资源隔离 | `ulimit -l` = **unlimited** · `VmLck 0 kB` / `VmPin 0 kB`（PLE 走 mmap，故意不锁） |
| 6 | 显存布局 | `expert cache auto: 22.88 GiB free, 700 MiB reserved (+218 MiB draft head) -> 6779 slots`；prompt 路径 **borrows 1554 槽（3.49 GiB）**；VRAM used 33,606,098,944 B / total 34,342,961,152 B（**VRAM free 0.69 GiB**） |
| 7 | 回滚件 | `-001`(在产) · `-002/003` · `-004`(0.9.0) · `-005`(H1) · `-006`(H2) · `-008`(ladder-5) · `-009`(K10) · `-010`(K10 复测) · `-011`(K13)；`ci/rollback.sh --exe strata-0.1.57-001 --apply` |
| 8 | 本轮改动 | 生产装机 **0 次**、引擎 **无净变更**；`disk=build=running` 三方 md5 均为 `5e63174dbd7cc04e5fa1b5fc455b2a73` |
| 9 | ROCm | 容器内 `.info/version` **10.1.0** · HIP **7.16.26323-0000000**(`hipconfig`) · clang **24.0.0git** · `ROCM_BUILD=7.14.0-gfx906+20260802001858`（容器内 env 现场取值） |
| 10 | llama.cpp | **b11062** · `3cf03257f219afbe7334045ff7c6a06ac68c627d` · 整树 hash `6feee58927d5f1efd38e72bbc1db061d`（镜像 `/src/BUILD-IMAGE.json` 现场取值） |

**二、主线** — `gfx906/mi50` @ 6501c28f · tag `mi50-0.2.11-r33-14` · **领先 78 / 落后 0** / merges 0 · **脏 0 行**（在 166 上）；上游基线与镜像 `/src` 同源。实验台账分支 `gfx906/lcpp-picks` @ `209d3ca2`。本机工作区**不是 git 仓库**，主线 git 只在 166。

**三、本次落生产** — 引擎：**无净变更**；**重启 0 次、停机 0 分钟、回滚 0 次**；镜像 / 容器 / config 全部未动。远端只有 `docker inspect` / `md5sum` / `rocm-smi` / `/health` / `docker exec` 只读命令，无任何写操作；`qq_*` 残留容器 0 个。

**四、进度** — 348 条 / 已结 266 / **76.4%**；队列 `R51` → `R95` → `R94` → `R91` → `R89` → `R46` → `R49` → `R50`（`R101` OPEN 随 `P392`，`R99`/`R100`/`R102` 均已 DONE_NEG）。

---

## 正文

**1. 先回答你可能没意识到的问题：新会话不会「记得」这段对话。** 本轮按你的要求上网核了 WorkBuddy 官方文档，`From-Beginner-to-Expert-Guide/Function-Description/Task-Bar` 原文：**「每个对话对应一个独立任务，任务之间互不影响，各自维护独立的工作空间与上下文。」** 同页还写「若未提前指定，WorkBuddy 会在新建任务时自动创建独立空间」。⇒ 交接不能靠聊天记录，只能靠**同一工作空间里的文件 + 一段自包含提示词**。官方文档里**没有**记载上下文压缩或会话迁移能力（Conversation 页只讲回退 / 编辑 / 刷新 / 引用 / 上传）；「记忆文件自动注入」也没查到专门页面，所以相关行在交接件里只标「会话观察」，提示词按最坏情况写死自包含。

**2. 三件资产 + 一道门，全部可机械验证。** ①`albus/w1034/HANDOFF_PROMPT.md:1`——**2319 字符**的可粘贴提示词，低于官方的 3000 字符折叠阈值，含工作目录、第一动作、权威件、生产值、全部致命铁律、收工仪式、未结边界；刻意**不写分母 / 队列数字**，避免每加一行账本就腐坏。②`albus/w1034/HANDOFF.md:1`——完整交接件（状态快照、权威件地图、23 条铁律分五组、门清单、未结项、最近三轮实测、10 个坑、保鲜规则、外网核实记录）。③`tools/handoff_check.py:1`——A–G 七组检查（文件齐全、提示词长度与 12 个锚点、SNAPSHOT 可解析、唯一队列与分母自洽、HARD 门齐全且自身在内、斜杠命令与最新报告存在、无硬编码漂移值），负向自测 **4/4**，`--live` 可只读核 166 的引擎 / config md5。已接进 `albus/w1002/round_close.py:23` 的 HARD ⇒ **每轮收工都会验交接件**。另做了 `.codebuddy/commands/strata-handoff.md`（`/strata-handoff` 快速通道），格式按 CodeBuddy Code 官方 slash-commands 文档的 frontmatter 规范。

**3. 你的迁移操作只有 5 步，最容易漏的是第 2 步。** 在同一空间分组上「新建任务」（Task-Management 官方记载）→ **手动把工作空间选成 `D:\workbuddy_space\strata_ws`** → 保持默认 Agent 模式 → 粘贴提示词（或 `/strata-handoff`，或 `@albus/w1034/HANDOFF_PROMPT.md`）→ 等它回报「交接自证 + 现行队列 + 生产健康」再下指令。旧会话**归档**而非删除：官方写明删除「无法恢复」。若新会话读不到文件，正确反应是报告「工作空间选错」，不是凭印象编结论。

**4. 主动补上的几件事（你的表达里没写，但缺了就会翻车）。** ①把「哪些内容会自动注入」列成表并分级：对话历史=不继承（官方）、工作区文件=选对目录才有（官方）、用户级长期记忆与工作区 `MEMORY.md`（2890 字符窗口）=会话观察、`MEMORY_DETAIL.md`（544 KB）与每日日志=不注入、生产现场值=永不注入。②把**全部铁律**搬进交接件而不只搬结论：停机需点头、166 只能断电冷启、装前断言单引擎、setsid+trap 回滚、禁 `present_files`、写文件禁同式 read+open、删除只进回收站、临时服务用完即停、Bash shim 五个坑、有技能必须用技能、产物进 `albus/`、人称反转与「你定/从严」的含义。③**保鲜规则**：提示词不写漂移数字，`SNAPSHOT` 只放稳定标识，`handoff_check` 每轮强制校验，交接件不同步 166（它描述本机文档与门，六件权威件才同步）。④把「历史报告里的分母 / 队列是当时快照」写清楚，现值一律现场跑 `progress.py` + 读 `§0.1`。⑤标出本机不是 git 仓库，避免新会话在本机跑 git 找版本。⑥给了换目录 / 换机器时的改写清单。⑦保留 `P392` 的停机前置条件，避免新会话一上来就跑数值门。

**5. 外网核实记录（全部可复查，不凭印象）。** Task-Bar：独立上下文、默认 Agent、未指定路径自动建独立空间、粘贴 >3000 字符折叠、项目级 slash commands 在 `.codebuddy/commands/`。Create-Task：选工作空间后基于该目录读写、`@` 引用文件 / 文档 / 规则、上传拖拽。Task-Management：已有任务继续发消息会带上下文、同空间分组可新建任务、删除不可恢复。Conversation：无压缩 / 迁移记载。CodeBuddy Code / WorkBuddy 的 `slash-commands` 文档：`.codebuddy/commands/*.md` → `/<文件名>`、YAML frontmatter 支持 `description`/`argument-hint`/`allowed-tools`/`model`、正文即 prompt、`$ARGUMENTS`。Overview 只有产品简介，不含会话机制。**未核到**：官方关于记忆文件自动注入的专门页面（站内检索无结果）⇒ 明确标注，不当保证。

**6. 收尾与门。** 账本加 `P405`（交接资产）/`P406`（官方机制核实）两行，分母 346/264 → **348/266 / 76.4%** 并回写 `deploy/W832_OPT_PLAN_V2.md:24`（唯一队列在 `deploy/W832_OPT_PLAN_V2.md:28`；`tools/audit_scope.py:1` 校验）；`tools/plan_single_source.py:39` 的活文档清单补上 W1034 报告。`ROUND_CLOSE` 全套门（10 道硬门 + kernel_curve + bundle + mirror）验收，`mirror_check --sync` 把六件权威件逐字节同步 166。生产零改动。

**7. 未结与边界（照旧，不因交接而变）。** `P392` 的 prefill-only LOGPOS 数值门仍需停生产 10–15 min，**未经你点头不执行**；`R51` 的 K10「免费」只在 prefill 2K/8K 形状成立；`P309`/`P335`/`R101` 保留 OPEN 并各带解除条件；约 50 条历史 OPEN 不是待办清单，队列只认 `§0.1`。新会话的默认状态是「生产零改动」，任何会停机的动作先问。

---

补充三句：① 交接件本身也遵守本项目的单源化——提示词不写现值、交接件只放稳定标识、分母与队列只读 `§0.1`，因此这轮之后再加账本行也不会让提示词过期；② 新产物在 `albus/w1034/`（`HANDOFF_PROMPT.md`、`HANDOFF.md`、`reply.md`）、`tools/handoff_check.py`、`.codebuddy/commands/strata-handoff.md`，改动的权威件为 `PROGRESS.tsv` / `W832_OPT_PLAN_V2.md` / `albus/w1002/round_close.py` / `tools/plan_single_source.py`；③ 唯一需要你动手的是**新建任务时选对工作空间**并粘贴提示词，其余都由新会话自证。
