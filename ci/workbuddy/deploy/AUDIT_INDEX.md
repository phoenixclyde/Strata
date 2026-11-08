# 审计索引（AUDIT6 → AUDIT29）

> **【AUDIT28 · 2026-11-07】** 上一条 AUDIT27 的更正仍成立，但本表现在**真的**由产物校验：每件编号审计有一条 `> VERDICT:` 机读行，`tools/audit_outputs.py` 逐件比对 P 列；39 件冻结派生产物由 `COMPANIONS:` 点名；合计与边界由 `tools/audit_index.py` 派生。

> **AUDIT27 更正（2026-11-07）**：旧抬头写「本表由 `albus/w831/make_ledger.py` 从总判行机械提取」——
> 实际上本表一直是手工维护的（AUDIT25 曾躺在 `deploy/` 一整天没登记，AUDIT26 才发现）。
> 现在**行数/幽灵行/合计/边界**由 `tools/audit_index.py` 机械校验，`--fix-total` 从表派生合计与上界。
> 下一轮**待审区间**的判定方法：跑 `python tools/audit_scope.py --list`，
> 它从记忆件标题 / `albus/w<轮>/` / `PROGRESS.source` 取并集再减覆盖区间；
> **不要**再跑 `albus/w831/audit12_scope.py`（它的 `W(\d{3})` 会把 W1006 读成 W100），也不要靠这张表往前推。

| 审计件 | 覆盖轮次 | P0 | P1 | P2 | P3 | 文件 |
|---|---|---:|---:|---:|---:|---|
| AUDIT6 | W776–W785 | 0 | 5 | 5 | - | `AUDIT6_W776_W785.md` |
| AUDIT7 | W786–W788 + R5 | 0 | 4 | 7 | - | `AUDIT7_W786_W788.md` |
| AUDIT8 | W789–W795 | 0 | 4 | 7 | - | `AUDIT8_W789_W795.md` |
| AUDIT9 | W796–W800 | 0 | 5 | 7 | - | `AUDIT9_W796_W800.md` |
| AUDIT10 | W801–W809 | 0 | 2 | 6 | 3 | `AUDIT10_W801_W809.md` |
| AUDIT11 | W810–W825 | 3 | 12 | 8 | - | `AUDIT11_W810_W825.md` |
| AUDIT12 | W826–W831 | 3 | 11 | 12 | - | `AUDIT12_W826_W831.md` |
| AUDIT13 | W832–W839 | 3 | 8 | 6 | - | `AUDIT13_W832_W839.md` |
| **AUDIT14** | **W840–W843** | **6** | **12** | **9** | - | `AUDIT14_W840_W843.md` |
| **AUDIT15** | **方案本体 `W832_OPT_PLAN_V2.md`** | **0** | **9** | **0** | - | `AUDIT15_PLAN.md` |
| **AUDIT16** | **W844–W853（10 轮 / 12 件）**；P0-4 **已撤回** | **4** | **9** | **10** | **3** | `AUDIT16_W844_W853.md` |
| **AUDIT17** | **W856–W862（7 轮 / 8 件）** | **3** | **6** | **5** | **1** | `AUDIT17_W856_W862.md` |
| **AUDIT18** | **W863（1 轮，第 1–11 轮）** | **3** | **3** | **2** | **0** | `AUDIT18_W863.md` |
| **AUDIT19** | **W863 之后：读屋顶实测 884 GB/s + 全部审计输出的整改台账**（非 P 分级）；**884 的适用范围已由 `AUDIT22` 限定为「大块连续读」**，瘦矩阵 280–350 | — | — | — | — | `AUDIT19_ROOFLINE_REMEDIATION.md` |
| **AUDIT20** | **W864–W875（12 轮 / 12 件）**；**16 条已整改 / 1 条误报撤回**；原误编 AUDIT19，已改 | **2** | **10** | **5** | **0** | `AUDIT20_W864_W875.md` |
| **AUDIT21** | **W876–W883 + 两件历史漏审（W838/W846）**，8 件 / 56,336 字节，**16 条全部整改**；**另发现 W708–W775 共 58 件 / 927 KB 从未被任何审计覆盖**（见该件 §4） | **4** | **7** | **5** | **0** | `AUDIT21_W876_W883.md` |
| **AUDIT22** | **整改类（对象=审计件自身 + 方案）**：884 分母的两层错、`AUDIT16` 摘要承载已撤回结论、新增 `param_pair_lint`（10 条提示）；方案侧改 3 处 | **2** | **1** | **1** | **0** | `AUDIT22_OUTPUT_REPAIR.md` |
| **AUDIT23** | **未审计面全扫：W886–W897（10 件）+ W708–W775 剩余（22 件）**；30 件从未被任何审计引用；1 条 P0 已回写横幅 | **1** | **2** | **1** | **0** | `AUDIT23_W886_W897_AND_W708_REMAINDER.md` |
| **AUDIT24** | **W900–W951（50 件，全部首次被审）**：2 P0（W909 专家格式误判 / W832 方案落后于账本）、16 P1、12 P2、4 需复核；**A 级复跑 3 次**（PMC 67.3%、pack 字节、生产 804 tok/s）+ 外网核对 2 次 | **2** | **16** | **12** | **0** | `AUDIT24_W900_W951.md` |
| **AUDIT25** | **W952–W985（34 轮）**：六轴全面审计；**AUDIT27 补分级**（原件 §1 明写 P0 2 / P1 7 / P2 6，此前四列全 `—` ⇒ 合计少算 15 条） | **2** | **7** | **6** | **0** | `AUDIT25_W952_W985.md` |
| **AUDIT26** | **W898–W899 + W986–W1005（22 轮，全部首次被审）**：3 处账本口径不一致 + 2 条上游数字错（#22174 方向/数字成立；**#31188「无性能栏」是误判，AUDIT28 已撤回**）；0 P0 | 0 | 3 | 2 | 0 | `AUDIT26_W898_W1005.md` |
| **AUDIT27** | **W1006–W1031（26 轮，全部首次被审）+ W706/W707 历史补审**：1 P0（活流程文档仍命令已废止的逐字节指纹门、且仍写 #29953 REJECTED）、8 P1（分母/队列、AUDIT25 漏分级、4 条陈旧 OPEN、R99 无关闭横幅、lcpp_picks 双副本漂移、W1020 缺报告、mirror_check 写死最新审计件、三位数 R 号门盲区）、5 P2；**逐轮清单 + 外网复核 5 条上游引用** | **1** | **8** | **5** | **0** | `AUDIT27_W1006_W1031.md` |
| **AUDIT28** | **整改类：22 件编号审计 + 39 件派生产物 + 2 本台账 + 方案本体**；1 P0（AUDIT26 对 #31188 的「PR 内无性能栏」误判，已全链撤回）、4 P1（机读总判 / 派生产物清单 / 方案单源化 / 行号指针）、3 P2（外网补核 / 退役理由 / 冻结件纪律）；**外网复核 5 组** | **1** | **4** | **3** | **0** | `AUDIT28_OUTPUT_REMEDIATION.md` |
| **AUDIT29** | **W1032–W1052（21 轮，全部首次被审）**：1 P0（方案「唯一队列」与账本冲突且结构损坏）、4 P1（CI_RUNS 生产行 run id 404 而 D7 只读状态列、5 条已结仍挂 OPEN、4 条 OPEN 却 done=1、ledger_lint 209 误报且无退出码）、6 P2（46 行表格损坏、32 份报告副本、R107 行自相矛盾、状态语义漂移、跨分支引用歧义、trap 缺陷复发）；**A 级复跑 3 轮**（W1049 相位 / W1051 配对 decode / W1052 PV 预算）+ **24 条 CI run 逐条 API 核对** + 166 在产与 93 处复核 | **1** | **4** | **6** | **0** | `AUDIT29_W1032_W1052.md` |
| **合计** | **W706–W1052 + 方案本体**（24 件有 P 分级） | **41** | **152** | **130** | **7** | — |


## 审计派生产物清单（AUDIT28，机器可验）

> 39 件 `W*_AUDIT / W*VERDICT / W*REVIEW` 与 `AUDIT17_CLOSURE.md` 是**冻结的历史证据**，逐字保留、不参与整改；但必须被点名，否则「所有审计输出」永远无法回答有多少件。`tools/audit_index.py` 的 `want[n]` 对同号文件只留最后一个，配套件原本会被静默覆盖。

COMPANIONS: AUDIT17_CLOSURE.md W708c_PARAM_AUDIT.md W709_AUDIT.md W713_AUDIT.md W713_AUDIT2.md W716_AUDIT.md W733_TELEMETRY_AUDIT.md W735_AUDIT.md W752_AUDIT.md W763_INVENTORY_AUDIT.md W764_PARAM_LANDING_AUDIT.md W765_PARAM_AUDIT_VERDICT.md W773_AUDIT.md W775_AUDIT.md W775_AUDIT_G.md W775_AUDIT_auditor2.md W775_AUDIT_delta.md W775delta_AUDIT3.md W775delta_AUDIT4.md W775delta_AUDIT5.md W775delta_BUILD_SWITCH_AUDIT.md W775delta_W27_SRC_VERDICT.md W775delta_W6_ATTN_LANECELL_VERDICT.md W775delta_W9_CONCURRENCY_VERDICT.md W787_R1_FAILURE_REVIEW.md W789_R5_TILEV_VERDICT.md W801_AUDIT9_REMEDIATION.md W851_HIPBLASLT_VERDICT.md W886_PARAM_EVIDENCE_AUDIT.md W906_KI_GFX906_KERNELS_VERDICT.md W911_THREE_ROUTES_VERDICT.md W912_KI_PORT_VERDICT.md W914_PARAM_MASKING_AUDIT.md W915_OBSERVATION_ENVS_AUDIT.md W920_PARAM_AUDIT.md W934_R65_REBASE_VERDICT.md W937_CI_BYPASS_AUDIT.md W939_SOURCE_TASK_AUDIT.md W966_CODE_LEVEL_VERDICT.md

| 类别 | 数量 | 门的判据 |
|---|---:|---|
| 编号审计件 | 23 | 每件一条 `VERDICT:` 且等于索引 P 列 |
| 配套/冻结件 | 39 | 必须出现在 `COMPANIONS:` 行，文件必须存在 |
| 结案台账 | 2 | id 唯一、状态枚举合法、撤回标记仍在 |

## 台账

- `AUDIT_LEDGER.tsv` —— AUDIT12 的 26 条结论逐条登记（id / 严重度 / 位置 / 问题 / 处置 / 状态），
  由报告表格**解析生成**，改报告后重跑脚本即可同步，不手抄。
  **【AUDIT28 口径】** `loc` 列里的 `W828:<行号>` / `W832:<行号>` 是 **2026-10-31 的证据定位快照**，不是可跟随的现行指针；历史台账不重写，现行位置一律按 `W832 §0.2` 导航读小节名。

## 本轮的纪律新增（AUDIT19）

- **撤回必须回写三处**：源头文档横幅 + 账本行 + 参数表条目。只改最新一篇 = 让旧文档继续骗下一个人。
  AUDIT19 的 17 条里 9 条都是「后一轮改对了、前一轮没标」这个形态。

## 仍未结清的（跨轮，需实测）

| 项 | 出处 | 状态 |
|---|---|---|
| `--spec-min-p` / `--pcie-frac` | W832 §4.1（P210） | **UNRESOLVED**：效应 ≤4.4% < 噪声 6.0%，保留现值。原停机条件（`ms/win` <2%）结构性失效，见 AUDIT13 P0-2 |
| `--pool-workers` | W833 §4.5（P214） | **UNRESOLVED**（AUDIT13 改判）：n=3、无 ABBA；read1300 实为 3/3 同向 |
| 数值债 `GDN_PP` | P213/P229 | **未测**（GDN_HEAD 已确认位等价，GDN_PP 无臂） |
| §6.8 的 AMD 开关覆盖面 | W828 §6.8、AUDIT12 P1-2 | 19 项里 2 项默认开、5 项测过、**10 项整组否决（P212）** ⇒ 「已穷尽」仍不成立 |
| 宽窗口 bit-exact | W829 L79 | **未做**（并发轴已关，优先级低） |
| 28 个 `STRATA_USE_HIP` 死块 | W839 §6、P227 | **未打开任何一块**；候选 `pcie_frac_auto` / `decode_defaults_arch_ok` |
| ~~MMQ 构建门~~ | AUDIT16 P0-4 / P232 / `R16` | **已撤（2026-11-01 00:4x）**：MMQ 一直是编着且默认开的（编译行 `-DSTRATA_PREFILL_MMQ=1`）；新的问题见 `R17`（MMQ/fused/FP16 各几层、`dequant` 相位语义） |
| ~~MMQ 层分布与 dequant 语义~~ | AUDIT16 §11 / `PROGRESS R17` | **已结（AUDIT23 复核）**：账本 R17 = **DONE**（P232 一行 banner + 相位复核）；索引此前仍写 OPEN，属陈旧项 |
| ~~`R22` 的口径~~ | AUDIT17 P0-1/P0-2 | **已结（W863）**：从 GGUF 张量表逐层枚举，GDN 6 张量 63.42 MiB / QSA 7 张量 55.45 MiB（36/12），与日志 499 矩阵 / 3619.14 MiB 逐字节吻合；每窗口 dense Q8_0 = 4263.24 MiB，占 **37.8%**；除数三分开（窗口 / 接受 token ÷1.79 / 列 ÷2.26）。见 `W863_R22_DENSE_BYTES.md` |
| ~~R 行数（每波几行）~~ | W862 §3.4 / `R23` | **已结（W863）**：216 格实测表替换了 W862 的公式（公式在 ncols=1 会倒扣 0.982×）；引擎 **0.1.55h** 已上生产，同镜像 A/B **+4.0%**。见 `W863_WAVE_ROWS_TABLE.md`、`W863_R23_DEPLOY.md` |
| **`gen_config.py` 已失效** | W863-2 | **OPEN**：`META` 仍指 `/src/build-906/strata` + 旧 pack，现在跑 `--write` 会写坏生产 config；改 config 只能「备份 + 定点改字段」 |
| ~~`build.ninja` 不可重生成~~ | W863-3 → **W994 更正** | **已推翻**：挂对 `/ref=llama_b12110`(ggml 0.29) + 透传 `--device=/dev/kfd --device=/dev/dri` 后，容器内 `cmake -S /src -B /out -G Ninja` 与 `ninja -j4 strata` 全通（RC=0），产物 md5 与生产逐字节相同。**保留的规矩**：单 TU 改动仍走 `ci/build.sh` 的三条逐字命令；全量重建必须以 md5 复现生产为验收门 |
| ~~HC 带宽只有 14%~~ | `R25` / `R27` / `R28` / `R31` | **已重算（AUDIT19）**：分母实测 **884 GB/s**（非 700）⇒ HC = **11.1%**；「慢 2.5×」因 6.89 ms 的 CV 约 ±30% 而**不成立**。已拆成 R27（混淆实验，降级）/ R28（34 字节布局，证伪）/ **R31（指令发射率，OPEN）** |
| ~~专家读字节未知~~ | `R26` | **已结（W863-6）**：`VRAM hits 8.85 + waitB 1.28 + PCIe 0.81 + copy 0.84 = 11.78 ms = 24.9%`，字节数已由 W891 给出（3.135 MB/专家槽、411 GB/s）；索引此前仍写 OPEN |
| **W857 的 ring 负对照** | AUDIT17 P1-1 | **降级 UNRESOLVED**：单臂、无 repeat、B 臂 TIMING 丢失 |
| ~~dequant 的摊薄空间~~ | AUDIT16 P0-3 / `R14 的残值` | **已并入 R14（DONE_NEG，W853 §3.1）**：融合路径编译期不可达且只吃 IQ 格式；账本行已补证据正文（AUDIT23 A23-5） |
| ~~`wait copy` 的**预取深度**~~ | AUDIT16 P0-2 / `R15 的残值` | **已结（AUDIT27 更正 2026-11-07）**：残值已由 `R98` 认领并判 **DONE_NEG**（W1014 三档 `PREFILL_RING=768` 为 −0.53/−0.61/−0.55%，越深越慢；W1013 的算术估计符号反了）。索引此前仍写「仍 OPEN」，与账本冲突 |
| ~~升级 v0.2.9 / 引擎 0.1.55~~ | AUDIT15 §6.11、`PROGRESS X12` | **已结（W844/W845）**：引擎 0.1.55g、`/src` 全树、门禁 17 项、TIP-OK |
| ~~分支基座 ≠ 构建树基座~~ | AUDIT15 §7 | **已结（W845）**：`gfx029` 就在 `aef9d25`（v0.2.9+1 提交），整树可编译、rebase 可用 |
| **峰值占比的分母（~700）从未实测** | **AUDIT19 / A9** | **已结**：STREAM 探针实测**读屋顶 884 GB/s（86.3% 规格）**、拷贝 752；峰值在 4 blocks/CU（1/CU 仅 55%）。全线重算：dense **29.8%**（原 37%）、GDN 48.3%、QSA 28.5%、head 44.1%、HC 11.1% |
| **R27 是混淆实验** | **AUDIT19 / A10** | **已结**：block 数与每 block 行数一起变 ⇒ 只能得"在该 kernel 内少 block 更快"，不能外推"占用率无用"。受控实测方向相反（55%→86%） |
| ~~镜像 `/src/serve/telemetry.py` 落后主线~~ | **AUDIT19 / A11** | **已结（AUDIT27 现场复核 2026-11-07）**：容器 `2d765942e041` 内 `/src/serve/telemetry.py` md5 **`94d6949d…`** 与 `gfx906/mi50` 树上同名文件逐字节相同，且 `git diff mi50-0.2.11-r33-14 -- serve/telemetry.py` 为空；修复提交 `6be218fc`（sampler thread refs）已在 `strata-gfx906:0.2.11-101` 镜像里。原文「下一次重建 0.2.9-102 必带」已被 0.2.11 取代 |
| **判据三档（5%/3%/2%）是拍的** | **AUDIT19 §5** | **已结**：统一为 `abs(Δ) ≥ 2×该次 run 的 CV`；实测噪声底最好 1.06%、常态 3.86–4.36%、冷机 18.36% |

## AUDIT27 新增的纪律（2026-11-07）

- **边界一律由产物推导**：`tools/audit_scope.py` 从记忆标题 / `albus/w<轮>/` / `PROGRESS.source` 取并集，
  减去覆盖表的区间；`tools/audit_index.py` 的合计与上界也改为派生。凡是「最新 X」「到 WNNN 为止」写死在脚本里，
  下一次新增就会让两份副本再次分叉。
- **审计债有上限**：尾部连续未审轮次 > 8 即 `ROUND_CLOSE` FAIL，不再靠人记得「该审了」。
- **撤回要覆盖活流程文档**：结论改在 `PICKS.tsv` 而指令留在 `README.md`，等于没改；
  `audit_scope §B` 直接拦「已废止判据以现行指令出现」。
- **门自己也会瞎**：`R\d{1,2}` 看不见 R100+、`W(\d{3})` 读不出 W1006、`mirror_check` 写死 AUDIT26。
  本轮起，凡是「枚举某类编号」的正则，都要用能覆盖当前最大位数的写法，并有负向自测。

## 结案台账（AUDIT24 起，机器可验）

- `AUDIT_LEDGER_A24.tsv` —— 每条发现一行：`id / 级别 / 文件 / 标志串 / 状态 / 处置 / md5`。
- `tools/audit_closure.py` —— 逐条校验"标志串是否还在文档里"：**任何一条撤回被后来的编辑删掉，脚本立刻 FAIL**。
  本轮：**33 行 / RESOLVED 33 / FAIL 0 / WARN 0**。
- 相关纪律：㉑ 账本行可机械验（`tools/ledger_lint.py`）· ㉒ 改表必体检 · ㉓ 引用方案给 `md5+行号` ·
  **㉔ 撤回必须带结论动词**（只改数字不算）· **㉕ 版本先后只能用正确 tag 的来源文件证明**。
