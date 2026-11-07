# W775_AUDIT_auditor2 -- 对抗性审计 W767-W775b（2026-10-11 03:2x）

> 审计员：**auditor2**（独立对抗性审计，read-only）
> 纪律：自称数字一律**独立复算**；转抄的标「转抄，未独立复算」；无证据的**明确写未取证**，不用推测填充；不做"总体良好"式空话。
> **立场**：凡"声称"必须找到**原始证据**才算成立；找不到->判 P1/P2；账本与证据冲突->**以证据为准**，并指出账本哪一行要改。

---

## 0 审计范围与取证方式

**范围**：workspace `D:/workbuddy_space/strata_ws`，2026-10-10 18:00 -> 2026-10-11 03:08 的 16 个工作轮（W767 / W767续 / W767续2 / W768 / W768收车 / W768续 / W769 / W770 / W771 / W772 / W773 / W773续 / W773续3 / W774 / W775 / W775b）。

**受审账本（任务给定快照）**：

| 文件 | 给定 md5 | 我实测 | 一致 |
|---|---|---|---|
| `.workbuddy/memory/2026-10-10.md` | eee4c982... | eee4c9825217ff860ebb59e712ef03ba（85,630 B） | [OK] |
| `.workbuddy/memory/2026-10-11.md` | 9c6e36a54b7c5e8c57063f769cd35d4f（21,921 B） | **审计中被改**：现 2c9d8be0b2b300963647663d743c918d（26,592 B, CR=0） | [NO] |
| `deploy/W713_PLAN.md` | 1d3d835d8cbe10b4282ccd241aa35c6d | 同（86,833 B） | [OK] |
| `deploy/W775_VERSION_SYNC_0142.md` | 572cbc09b6f2cd4b7e65c9b64aa55f9c | 同（16,723 B） | [OK] |
| `.workbuddy/memory/MEMORY.md` | 703eb95d68fc107540af99dfb76b10f2 | 审计中先一致（4,228 B），后被另一会话改为 6f170e515c56a0a6786d6a022ed2e555（4,211 B） | [NO]（见 E） |
| `deploy/params/PARAM_REGISTER.tsv` | c28a7c89713a077aae97add9f714cc44 | 同（76 行 = 1 表头 + 75 数据，11 列） | [OK] |

**取证方式**：本地文件 `md5sum`/字节/字符（Python 码点）/CR 计数全部自算；远程 166 仅 **read-only** 实况复核（`curl /v1/status`、`/metrics`、`docker ps -a`，经 Python `subprocess.run(["ssh",...])` argv 调用 + base64 管道脚本，无写操作）；GitHub API 匿名只读核对 PR/issue 状态与标题；KL 数值用 `_w767_logpos_*.tsv` 原始 logpos 独立重算两方向。

**[!] 快照一致性违规（先行声明）**：审计期间 **`.workbuddy/memory/2026-10-11.md` 被另一会话写入**（21,921 B/md5 `9c6e36a5...`/CR=35 -> 26,592 B/md5 `2c9d8be0...`/CR=0，mtime 03:12）；同时 `MEMORY.md` 也被改（见 E）。**受审对象在审计中变动**，导致"给定快照 vs 现盘"不可直接对齐。本报告对每个数字均注明取自哪一版；凡依赖被改文件的判定，以我**该瞬时**实测为准并注明。

---

## 1 缺陷汇总

| # | 级别 | 条目 | 声称 | 实证 | 判定依据 |
|---|---|---|---|---|---|
| 1 | **P1** | A 生产升级 0.1.42 验收快照 | W775 称升级即 `/v1/status`+`/metrics` 双处 `32GB`、推理 4.1s/40tok、`draft 25/27`、`verify_config.py PASS=26 FAIL=0` | 盘上验收快照 `_t407_verify.txt`（02:29）`/v1/status` = **`Radeon Instinct MI50 16GB`**；`last_timings:null`、`requests:0`；**全盘无 4.1s/40tok、25/27、PASS=26 任何字样**。live 现盘 `32GB`/engine 0.1.42/pcie gen3 width16 均 [OK] | 现盘为"现状回填"到历史；升级当刻 16GB 与"双处 32GB"矛盾 |
| 2 | **P1** | A `verify_config.py PASS=26` 证据 | W775 称已跑并 PASS=26 FAIL=0 | 我**自跑** `deploy/params/verify_config.py` 得 `PASS=26 FAIL=0`（锚定 live 容器）--**该项成立**；但**升级当刻的盘上无此输出**，属事后补跑 | 结论可复现但非"升级验收时"取证 |
| 3 | **P1** | C "全部 PR 已审无悬空件" | W775b todo #14 表列 #1877 open / #1855 open / #1733 closed / #1732 closed / #1731 closed，称"其余全部 closed，无悬空件" | API：#1734/#1735 为 **issue**（`is_pull_request=False`）**仍 open**、0 评论、无 label；W774 明写"#1734/#1735 are issues still open" | 表**只列 5 个 PR**，漏 2 个 open issue -> "无悬空件"对 issue 不成立 |
| 4 | **P2** | C #1855 行数 | 账本记 #1855 `+847` | API 实测 `additions=854, deletions=0` | 数字偏差 7 行（可能为时点差） |
| 5 | **P2** | F 解码侧离散度选择性上报 | W774 称解码侧弃权（臂内离散 16-21%） | 我复算：p41 small 21.0% / large 16.2%、sw1 large 9.2% [OK]；但**small 档多臂离散 >100%** 未被并列呈现 | 离散度仅报"支持弃权"的分档，选择性 |
| 6 | **P2** | M MEMORY.md CANDIDATE 计数 | MEMORY.md 第 50 行称 "CANDIDATE 9" | 同处实际列出 **11 个编号**（P33·P41·P42·P46·P47·P48·P97·P55/P56/P59/P60） | 计数与枚举不符 |
| 7 | **P2** | I 归因作废的残留引用 | W767 归因经 W768/W769 判"作废" | P04 证据行 + `W713_PLAN.md` 条 39 仍写"剂量-响应成立"，**无作废指针** | 作废结论未回写所有引用处 |
| 8 | **P2** | L 写通道判据不稳 | W770 无 token -> W771"可用" -> W774"不可用" -> W775"可用" | 三次翻转；最终结论（可用）经 `_tok.txt` 真实 token + #1877 open 验证**正确** | 判据随会话摇摆，非稳定判据 |
| 9 | **P2** | 快照一致性 | -- | `2026-10-11.md` 与 `MEMORY.md` 审计期间被并发写入 | 审计对象变动，破坏可复算性 |

> 级别定义：**P0**=结论错误/伪造证据 · **P1**=证据不足/口径不严 · **P2**=措辞/表述。
> **本审计未发现任何 P0**（含最高优先的 D 项"伪造佐证"嫌疑--经查证**证伪**，见 §2-D）。

---

## 2 逐条核查明细

### A. 生产升级 0.1.42（W775）

**声称原文**：升级后 `/v1/status` 与 `/metrics` **双处** `engine:0.1.42`、`gpu_name=Radeon Instinct MI50 32GB`、`gpu_pcie_gen=3`/`width=16`；推理 4.1s/40tok；`draft_n_accepted 25/27`；`verify_config.py PASS=26 FAIL=0`；回滚容器 `strata166-407_0141bak` 保留。

**取证**：
- 盘上验收快照 `deploy/tmp/_t407_verify.txt`（02:29，2450 B，截断于 `"hardware": {"gpu_util": 0,`）：
  - `/v1/status` -> `"machine":{"gpu":{"name":"Radeon Instinct MI50 **16GB**", ...}}`、`"engine":"0.1.42"`、`"uptime_s":9`、`"activity":{"requests":0}`、**`"last_timings":null`**。
  - `/metrics` -> `"version":"0.1.42"`、`"engine":"0.1.42"`、`"kv":"k8v4"`、`"expert_slots":9761`。
  - 文件末端 `===ERR==`，**无 verify_config.py 输出**。
- `deploy/tmp/_t407_after_patch.txt`（02:33）-> `READY`、`engine.version 0.1.42`、`expert_slots 9761`。
- `deploy/tmp/_v42_rebuild_out.txt` -> CMD 为 `/src && exec python3 serve/server.py ...`；两容器：`strata166-407 | strata-gfx906:0.1.42 | Up`、`strata166-407_0141bak | strata-gfx906:0.1.41 | Exited (0)`。
- **全盘 grep**（`_t407_verify/_t407_after_patch/_v42_rebuild_out/_w775_auto/_w775_auto2`）对 `4.1`、`40 tok`、`25/27`、`draft_n_accepted`、`PASS=26`、`FAIL=0` -> **全部 0 命中**。

**实测（live，只读，03:2x）**：
- `/v1/status` -> `machine.gpu.name = **Radeon Instinct MI50 32GB**`、`engine=0.1.42`、`uptime_s=2571`、`requests=5`。
- `/metrics` -> `engine=0.1.42`、`kv=k8v4`；`hardware`：`gpu_pcie_gen:3`、`gpu_pcie_gen_max:3`、`gpu_pcie_own_gen:4`、`gpu_pcie_width:16`、`gpu_pcie_path:"4/4"`。
- `docker ps -a` -> `strata166-407 | strata-gfx906:0.1.42 | Up 46 minutes`；`strata166-407_0141bak | strata-gfx906:0.1.41 | Exited (0) 54 min ago`；另有 `strata166-406`（0.1.41，2 天前退出）。
- 我自跑 `python deploy/params/verify_config.py` -> **`PASS=26 FAIL=0`**。

**判定：PARTIAL / P1**
- [OK] 成立：live 双处 engine 0.1.42；live gpu_name 32GB；pcie gen3/width16/path4/4；两容器并存（回滚件在）；`verify_config.py PASS=26 FAIL=0`（**我自跑复现**）。
- [NO] 不成立/缺证：
  1. **升级当刻的盘上快照 `/v1/status` = `16GB`**，与账本"双处 32GB"（若指升级验收时）**冲突**。现盘 32GB 疑似为**现状回填**到历史叙述。
  2. **4.1s/40tok 与 `draft_n_accepted 25/27` 在盘上零证据**；验收快照 `last_timings:null`、`requests:0`，说明取快照时**尚未推理**，故"升级即测得 4.1s/40tok/25/27"**无原始证据**。
  3. **PASS=26 是事后自跑**，非升级验收时盘上留痕。
- **账本须改**：`2026-10-11.md` W775 段"升级后双处 32GB / 4.1s/40tok / draft 25/27 / PASS=26"应标注**取证时点**，并注明盘上验收快照彼时为 16GB、`last_timings=null`--即**删除"升级即双处 32GB"的既成叙述**，改为"升级后经 telemetry 补丁，`/v1/status` 现为 32GB（升级当刻快照为 16GB）"。

### B. PR #1877（W775/W775b）

**声称**：已创建；`serve/telemetry.py +16 -1`；`mergeable_state: clean`；**0 评论**；base = upstream main HEAD `61b3fb5dd3f1e8ec09cf7e4e05208bc6d3c46406`；分支 `amd-monitor-name-consistency`。

**取证（GitHub API 匿名只读）**：`#1877 state=open`、`base.sha=61b3fb5dd3f1e8ec09cf7e4e05208bc6d3c46406`、`head.ref=amd-monitor-name-consistency`、`additions=16 deletions=1`、`mergeable_state=clean`、`comments=0`。

**判定：PASS** -- 六项**全部逐字一致**。

### C. "全部 PR 已审，无悬空件"（W775b todo #14）

**声称**：#1877 open / #1855 open / #1733 closed / #1732 closed / #1731 closed；"其余全部 closed，无悬空件"。注：W774 曾说"#1734/#1735 are issues still open"。

**取证（API）**：
- `#1734`：`is_pull_request=False`（**issue**）、`state=open`、`comments=0`、`labels=[]`。
- `#1735`：同上，**issue、open、0 评论、无 label**。
- `#1855`：`additions=854 deletions=0`（账本记 `+847`）。
- 其余 #1733/#1732/#1731 确为 closed。

**判定：FAIL -> P1（+P2 行数偏差）**
- W775b 表**只列 5 个 PR**，**漏掉 2 个仍 open 的 issue**（#1734/#1735）-> "无悬空件"对 issue **不成立**；且与 W774 自记"仍 open"**自相矛盾**。
- **账本须改**：W775b todo #14 表须补 #1734/#1735 两行（issue、open），并把"无悬空件"改为"PR 无悬空；**issue #1734/#1735 仍 open**"。

### D. #1729 守卫链两互斥陈述 -- 最高优先

**声称交叠**：
- W775 草稿 v2 称"0.1.41 的 HIP 路径仍会到达 `by_default=true` 调用点"；
- W775b **推翻**：真实机制是**编译期宏选择**（`#if !defined(STRATA_USE_HIP) && !defined(STRATA_HIP_GFX906)`），并**逐字引用 PR #1732 标题**作为佐证。

**关键怀疑**：若 #1732 标题与引用不符 -> **伪造佐证 -> P0**。

**取证**：
- `deploy/tmp/_pf_ctx.txt`：
  - 第 2 行 `67c1d3d19ff50b344bea917362386ff2  /src/src/prefill/prefill.cpp`。
  - 第 14-18 行：`1867:void Prefill::arm_cpu_share(bool applies, bool by_default) {`、`1868:#if !defined(STRATA_USE_HIP) && !defined(STRATA_HIP_GFX906)`、`1869-1870: g_share_default = true;`、`1876: (void) by_default;`。
- GitHub API：`#1732 title = "prefill: the gfx906 build reached the CUDA branch of arm_cpu_share"`。
- `deploy/tmp/_w775_ghcheck.txt` 第 22 行同样记 #1732 closed 且标题一致。

**实测**：md5 一致 [OK]；`#if` **确实**含 `&& !defined(STRATA_HIP_GFX906)` [OK]；`(void) by_default;` **确实存在** [OK]；**PR #1732 标题逐字一致** [OK]。

**判定：PASS（伪造佐证嫌疑**证伪**）** -- W775b 的**推翻正确**：真实机制为编译期宏选择，`by_default` 被 `(void)` 显式弃用；W775 草稿 v2 的"HIP 路径仍到达 `by_default=true` 调用点"为**误判**。
- **账本须改**：确认 `2026-10-11.md` W775b 已把 v2 结论标为作废；若无，须补作废标记。

### E. MEMORY.md 写入（W775b）

**声称**：chars `2,899 -> 2,897`、bytes `4,228`、md5 `703eb95d68fc107540af99dfb76b10f2`、CRLF=0、`VERIFY=OK` 七项全 PASS。

**取证**（自算）：
- `.workbuddy/memory/MEMORY.md`：**chars（Unicode 码点）= 2,897**、**bytes = 4,228**、**md5 = 703eb95d68fc107540af99dfb76b10f2**、**CR 计数 = 0** -> **四项与声称逐一吻合** [OK]。
- `deploy/tmp/_w775_auto.out.txt`：`现状 chars=2893 bytes=4259` -> CONTENT 操作 -> `chars=2899 bytes=4234`。
- `deploy/tmp/_w775_auto2.out.txt`：`chars=2899 bytes=4234` -> `AFTER chars=2897 bytes=4228`；`ARCHIVED Z-48 : DETAIL 213713 -> 218156 bytes (+4443)`；`WROTE MEM chars=2897 bytes=4228 md5=703eb95d68fc107540af99dfb76b10f2`；七项验证 PASS（含 `[PASS] P 编号零丢失`、`[PASS] DETAIL 前缀未改`）、`VERIFY = OK`。
- `.workbuddy/memory/MEMORY_DETAIL.md`：现 **218,156 B** [OK]（与 +4443 一致），Z-45/Z-46/Z-48/Z-49 段落齐备。

**判定：PASS**（针对给定快照）
- [!] **但审计中该文件被另一会话再改**：现 `4,211 B / md5 6f170e515c56a0a6786d6a022ed2e555`（另见 §0 快照违规）。**E 项判定只对我实测吻合的那一瞬（4,228 B / 703eb95d...）有效**。

### F. W774 五臂读数（解码弃权）

**声称**：prompt 侧 P55/P56/P59/P60 全中性 `|delta|≤0.4%`；解码侧弃权（臂内离散 16-21%）。

**取证**：`deploy/tmp/_w774_all.json`（19,007 B，`###ARM <name>` + JSON 数组）解析得 5 臂 p41/p42/sw1/sw2/hm1，**每臂 records=4** [OK]；**all `reused=0`** [OK]。

**实测（自算 `|delta|`）**：
- prompt 侧小档：P55 `-0.003%`、P56 `+0.049%`、hm1 `+0.046%`；大档：P55 `-0.07%`、P56 `~0.00%`、hm1 `+0.379%` -> **`|delta|≤0.4%` 成立** [OK]。
- 升级 p41->p42：小档 `-3.36%`、大档 `-0.69%` [OK]。
- 解码侧离散：p41 small `21.0%`/large `16.2%`、sw1 large `9.2%` -> 与账本 16-21% **吻合** [OK]；但 **small 档多臂离散 >100%** 未并列（选择性）-> P2。

**核心挑战复核**：账本 §2 自认 `_w773_speed.py` 的 `filler()` 读了镜像自带 `/src` 树，致 p41 小档 `26036 tok` vs p42 `23781 tok`（**+9.5%** 输入差）。我核对：该 +9.5% 输入差**只影响 p41 vs p42 的小档对比**；4 个 opt-in 对比（P55/P56/P59/P60）输入均 ~2378x、**不受影响**。

**判定：PARTIAL（主体成立，P2 选择性上报）**
- prompt 侧"小档 `|delta|≤0.4%`"**仍成立**（输入差不在该 4 组）。
- 账本"clean and judgeable"**基本站得住**，非 P0；但解码侧离散度的分档上报不完整 -> 降级为 P2。

### G. W773 P46（`STRATA_IO_PREFETCH`）

**声称**：REJECTED；"参数生效，但预取 0 次"。

**取证**：
- `deploy/tmp/_w773_B.log` **原始证据**：第 20 行 `strata generate: file tier io prefetch ON (STRATA_IO_PREFETCH=1): whole-blob preads, ... 8 I/O threads`（**生效** [OK]）；第 68/75/82/89 行**四请求**均 `io prefetch: 0 read ahead (0.0 MB by pread), 0 used, 0 unused, 0 skipped (cached), 0 dropped`（**0 次** [OK]）。
- `deploy/tmp/_w773_A.log`（对照）：第 67-88 行 `file tier I/O this request: ...`，**无 io prefetch 字段** [OK]。
- `deploy/tmp/_w773_ab.out`：各臂"P46 判定"段仅印 `engine --kv: --kv k8v4`，无预取证据（账本另附 B.log）。

**判定：PASS** -- "生效"与"0 预取"**均有运行期原文**（非仅源码推断），REJECTED 成立。

### H. 账本自洽性

**取证**：`W713_PLAN.md` §6.4 表 #1–#14 **连续、无缺号、无重复** [OK]；`PARAM_REGISTER.tsv` **75 数据行、11 列统一** [OK]。

**判定：PASS**。

### I. W767/W768 "自推翻链" -- 最高优先

**声称**：W767 给 `--kv` 四档质量门结论 -> W768 称"驻留控制未排除混淆，混淆与主效应同量级 => W767 归因作废" -> W769"补充严格匹配驻留对照"。

**取证 + 独立重算（`_w767_logpos_*.tsv`，每文件 1986 行）**：

| 量 | 账本 | 我复算 | 一致 |
|---|---|---|---|
| `KL(f16a‖k84)` @808 | 0.404158 | **0.404157** | [OK] |
| `KL(k84‖f16a)` @808 | 0.484061 | 0.483974 | [OK]（**两方向显著不等**，非对称已声明） |
| W768 `rc9 vs rc6` | 0.36554 | **0.365537** | [OK] |
| W768 `rf6 vs rc6` | 0.51594 | **0.515929** | [OK] |
| W769 `p131 vs p122` | 0.28731 | **0.28730** | [OK] |
| W769 `p122 vs p114` | 0.30449 | **0.30449** | [OK] |
| W769 `p131 vs p114` | 0.28639 | **0.28639** | [OK] |
| W769 `f16a vs rf6` | 0.28370 | **0.283696** | [OK] |
| 自比 | 0 | **0** | [OK] |

- (a) W768"同量级"有具体数字：`rc9 vs rc6 = 0.3655` 对应主车 `0.404`，同量级 [OK]。
- (b) W769 以 `MC*=117446` 严格匹配驻留，slot 记录 9761/9598/9696/9794 与账本一致 [OK]。
- (c) W767 归因**确已作废**：`W767_KV_QUALITY_GATE.md` §8 第 217 行`-> §3 的因果归因不成立 -- 本件的第 2 条结论作废`，第 240 行重申；`W769_RESIDENCY_MATCHED_KV.md` §5 第 121/123 行已标"W773 更正"（0.48406/0.119 方向反->0.039）。**未再把 W767 归因当有效使用**。

**判定：PASS（含 P2 残留）**
- 声明的"混淆同量级""驻留匹配""归因作废"**均有原始数据 + 我独立复算支撑**。
- **残留 P2**：`PARAM_REGISTER.tsv` P04 证据行 + `W713_PLAN.md` 条 39 仍写"剂量-响应成立"**未标作废指针** -> 须回写。

### J. W767(续2)/W768(续) 三处工具/压缩器缺陷

**声称**：(1) 五断言"P 编号齐"是空断言；(2) 压缩器两处静默语义丢失。

**取证**：
- `deploy/tools/mem_slim.py`（md5 `6ca05c39cd391a3fba5af5319ace7874`）：
  - 第 137 行 `chk(bool(nums), 'P 编号存在', ...)`（由旧"P 编号齐"**改名**）；
  - 第 145-146 行**新增** `P 编号零丢失` 集合差（set-diff）比对；
  - 第 285/563 行**独立检查**亦使用 `P 编号零丢失`。
- `_w775_auto.out.txt`/`_w775_auto2.out.txt` 中 `[PASS] P 编号零丢失` 与 `[PASS] DETAIL 前缀未改` 实跑通过。

**判定：PASS（缺陷已修）** -- "空断言"缺陷**已修**（空断言->集合差零丢失断言）。**风险评估**：现 `mem_slim.py` **不再携带空断言**，W775b 写 MEMORY.md 走的是已修版本，故 E 项写入可信。

### K. W770 上游社区 bench 两臂

**声称**：`--kv` 两臂跑上游 speed + needle，23:04 停，pull 8/8；needle 侧结论：`k8v4` 无损失（生产 `k8v4` 的关键判据）。

**取证**：
- `deploy/tmp/_w770_needles_k84b.json`：6 条 **全部 `found:true`**，word/answer 与对照**逐条相同** [OK]。
- `deploy/tmp/_w770_needles_f16b2.json`：6 条全 `found:true` [OK]。
- `deploy/tmp/_w770_needles262_k84b.json`：`[]`（**跳过**，非失败）[OK]。
- `deploy/tmp/_w770_speed_k84b.json`：**9 条**（4096/32768/128000 x 3），**全部 `reused=0`** [OK]；prompt 中位数 393.8/460.7/458.8，与账本一致 [OK]。

**判定：PASS** -- 6/6 needle 命中 + 9 条 speed 齐备，"k8v4 无损"判据成立。
- [!] 未取证：起停日志（"23:04 停、pull 8/8"）我没有对应的原始起停日志文件，**此项未独立取证**（见 §4）。

### L. W771 自纠 + 写通道三陈述

**声称时间线**：
- W770：无 token（写通道未知/不可用）；
- W771："凭据通道实际可用--此前陈述有误"（**第 1 次翻转：不可用->可用**）；
- W774："写通道不可用"（**第 2 次翻转**）；
- W775b：翻回"可用"（**第 3 次翻转**），并创建 #1877。

**取证**：`deploy/tmp/_tok.txt` 存在真实 token（`[REDACTED_GITHUB_TOKEN]`，40 字符）；#1877 经 API 确为 open（即写通道**确曾成功**）。

**判定：PARTIAL** -- **共三次翻转**（可用->不可用->可用），**判据不稳定**（P1/P2）。**最终结论（可用）正确** [OK]（有真实 token + #1877 落库佐证）。

### M. W772 "三处账本-实况差异更正"

**声称**：更正三处差异（含 W750 大小 `18,674 -> 18,477`、P50 名"三车"->"四车"等）。

**取证**：
- `deploy/W750_MASTER_PLAN.md` 备份实证：`.bak_w772_20261010_232147 = 18,674 B` -> `.bak_w773b_20261010_233823 = 18,477 B`，现 `18,613 B` -> **`18,674 -> 18,477` 成立** [OK]。
- `PARAM_REGISTER.tsv` P50 名称 `--kv 四档质量门读数（W767-W770）`、结论"（W767/W768/W769/W770 **四车**）"，**无"三车"残留** [OK]。
- MEMORY.md P33 确在 CANDIDATE [OK]。

**判定：PASS（更正正确）**；**新增问题**：MEMORY.md 第 50 行"CANDIDATE 9"**实列 11 个编号** -> P1（§1 #6）。

### N. 18:00 后 `PARAM_REGISTER.tsv` 全部变更

**取证**：
- P46 = CANDIDATE + P54 指针 [OK]；
- P55/P56/P59/P60 = `1(已测-prefill中性)`、CANDIDATE [OK]；
- P58 = PLE closure [OK]；
- P04/P50 = 已携带作废归因措辞（P50 结论"四车"）[OK]。

**判定：PASS**（除 §1 #7 的 P04/W713-39 残留 P2）。

---

## 3 结论

**可用（PASS）**：
- **B** PR #1877 六项全对；**D** #1729 守卫链 W775b 推翻**正确**（伪造佐证嫌疑**证伪**，非 P0）；**E** MEMORY.md 五项自算全吻合（限给定快照）；**G** P46 REJECTED 有运行期原文；**H** §6.4 连续/register 规整；**I** 全套 KL 数值**独立复算吻合**、归因**确已作废**；**J** mem_slim.py 缺陷**已修**；**K** needle 6/6 + speed 9 条；**M** 更正正确；**N** 登记一致。

**须更正（P1）**：
1. **A**：删除"升级即双处 32GB / 4.1s/40tok / draft 25/27 / PASS=26"的既成叙述--盘上验收快照彼时 `/v1/status`=**16GB**、`last_timings=null`、`requests=0`；PASS=26 系事后自跑。
2. **C**：W775b todo #14 表补 **issue #1734/#1735（open）**，删"无悬空件"。
3. **M(新)**：MEMORY.md"CANDIDATE 9"改为与枚举一致的 **11**。

**须补证（P2 级）**：
- **F**：解码侧 small 档 >100% 离散应并列呈现；**I**：P04/W713-39 补作废指针；**L**：写通道判据摇摆，建议固化为"token 可 `git credential fill` 且 PR 可落库"的稳定判据；**K**：起停日志（23:04/pull 8/8）补齐；**§0**：审受文件在审计中被并发写入，须冻结快照后复算。

**账本须改的具体行**（汇总）：
- `2026-10-11.md` W775 段（A）--加取证时点、改"双处 32GB"叙述；
- `2026-10-11.md` W775b todo #14 表（C）--补 #1734/#1735；
- `MEMORY.md` 第 50 行（M）--"CANDIDATE 9"->11；
- `PARAM_REGISTER.tsv` P04 证据行 / `W713_PLAN.md` 条 39（I）--加"[归因作废]"指针；
- `PARAM_REGISTER.tsv` #1855 行数（C）--`+847`->`+854`（或注明时点）。

---

## 4 未能取证项（诚实列出）

1. **A** 的"4.1s/40tok""`draft_n_accepted 25/27`"：**全盘零证据**，验收快照 `last_timings:null`。**未能取证**（非"证伪"，为"无据"）。
2. **A** 升级当刻 `verify_config.py` 输出：**盘上无留痕**，我的是事后自跑（结论可复现，但非当刻取证）。
3. **K** 起停日志（"23:04 停、pull 8/8"）：**未找到对应原始日志文件**，未能独立取证。
4. **L** 三次翻转的**逐次时间戳原文**：我据文件内容 + 现行状态推断次数，**未逐一取到各次翻转的原话时点**。
5. **账本快照一致性**：`2026-10-11.md`（及 `MEMORY.md`）在审计中变动，**"给定 md5" 与 "现盘 md5" 不可对齐**；本报告凡涉此二者，均以我瞬时实测为准并注明。
6. **`_t407_verify.txt` 截断**：`/metrics` 尾部（`"hardware": {"gpu_util": 0,` 之后）缺失，故该文件内 `gpu_pcie_gen/width` **当刻取值未能从该快照取证**（现盘 live 值已另行取证）。

---

*审计员 auditor2 · read-only · 2026-10-11 03:2x · 本报告未修改任何受审文件（仅新建本报告文件）*


> **[BAN 归一说明 · 2026-10-11]** 本件属"活跃交付件"，已按项目禁用码位表（见 `W750_MASTER_PLAN.md` 第 0.5.7 节）做 **ASCII 归一**，映射：`U+2192`->`->` · `U+21D2`->`=>` · `U+2026`->`...` · `U+0394`->`delta` · `U+00D7`->`x` · `U+2014`->`--` · `U+2605`->`命中`/`*` · `U+2460-U+2469`->`(1)-(10)` · `U+2705`->`[OK]` · `U+26A0`->`[!]`。
> **引文处语义一字未改**，原文形态可回溯：改前副本 `deploy/tmp/_w21_bak/`（改前 md5 见件尾注）。
> 改前 md5 = `d3a3fbb99e9e63c604a61228352c728f`（字节 23111）。
