# AUDIT28 — 整改所有审计输出 + 方案单源化（2026-11-07）

> VERDICT: AUDIT28 P0=1 P1=4 P2=3 P3=0 src=本件 §0 总判（AUDIT28 立，非轮次审计）

机主令：「整改所有审计输出，并优化调优方案。该上网查一定要上网查，不要自己猜。」
时间 2026-11-07 01:5x–02:3x。**生产零改动**（未重启、未换引擎、未改 config），全部取证为只读
（本机文件 + GitHub API + AMD 官方文档）。本件对象不是某一批轮次，而是 **64 份审计输出本身**与
`W832_OPT_PLAN_V2.md` 这唯一方案。

## 0 总判

**P0 = 1，P1 = 4，P2 = 3；8 条已全部整改。**

| id | 级别 | 位置 | 缺陷 | 处置 |
|---|---|---|---|---|
| A28-1 | **P0** | `AUDIT26 §2` + 方案 3 处 + 账本 4 行 + `AUDIT_INDEX` 1 行 + `tools/plan_retired.py` 1 行 | 审计件把「#31188 PR 内没有性能栏、17.2% 无法核实、只能写作者称」当作**外网复核结论**（AUDIT28 判为误判），并据此把方案里的数字降级、写进退役门。**这是假的**：PR #31188 正文有 `### Performance` 对照表 | 全链撤回 + 换正确理由（数字属实，CUDA/MoE 融合路径在 gfx906 不适用）+ 新门拦「撤回结论以现行事实出现」 |
| A28-2 | P1 | 22 件编号审计 + `AUDIT_INDEX` P 列 | 8 件没有统一「总判」小节（AUDIT15/18/19/20/21/22/25/26），其余 14 件格式各异；索引 P 列**只能手抄**（AUDIT24 曾差 1、AUDIT25 曾整行 `—`） | 每件补一条 `> VERDICT: AUDIT<n> P0=.. P1=.. P2=.. P3=..` 机读行；`tools/audit_outputs.py` 逐件比对索引 |
| A28-3 | P1 | `AUDIT17_CLOSURE.md` + 39 份 `W*_AUDIT / VERDICT / REVIEW` | 派生产物在索引里**无名**；`tools/audit_index.py` 的 `want[int(n)] = f` 同号只留最后一个，配套件被静默覆盖 ⇒ 「所有审计输出」到底有多少件无法回答 | `AUDIT_INDEX` 加 `COMPANIONS:` 清单 + 台账口径；新门校验 `audit_ish() == 编号件 ∪ COMPANIONS` |
| A28-4 | P1 | `W832_OPT_PLAN_V2.md` §6.5 | 20 行自持「队列」文字、10 处带日期的「重排/执行顺序/队列第 1 序」快照、26 个回写块无目录、1 处仍写「当前按 §6.5 顶部排序」 | 新增 `§0.2 本件怎么读`、`§6.5.0 回写块目录`（26 块全覆盖）、§6.5 抬头历史快照横幅、4 处陈旧声明改标；`tools/plan_single_source.py` 硬门 |
| A28-5 | P1 | 15 个 `W832:<行号>` 指针 | 行号随每次回写漂移（原指向第 2055 行的那个指针现在落在空行）；其中 6 处在活文档 | 活文档全部换成小节名；`AUDIT_LEDGER.tsv` 的 `loc` 列是 AUDIT12/13 的**历史证据定位**，冻结不重写，改在索引台账写明口径；新门禁活文档写行号 |
| A28-6 | P2 | 外网引用面 | 审计输出里 4 组外部事实只有二手转述，没有官方出处 | 逐条查 GitHub API / AMD 官方页（§2），把「成立/需收紧/未复核」写清 |
| A28-7 | P2 | `tools/plan_retired.py` 第 6 条 | 退役理由写成「#31188 contains no benchmark」（AUDIT28 已撤回该理由），把**真数字**当假数字退役 | 改理由为「PR 确有 2911.4→3410.8，退役是因为 gfx906 路径不适用」；数值本身仍不许当现行事实出现 |
| A28-8 | P2 | 冻结件与记忆件 | `W986_PLAN_V3.md`（已标 SUPERSEDED）、`AUDIT_LEDGER.tsv`、`.workbuddy/memory/2026-11-05.md` 里仍留旧口径与旧行号 | **不逐字重写历史**（W1007 曾机械改 10 份历史件再回滚）；只在 AUDIT28 与索引登记，并让门只扫活文档 |

## 1 范围：64 份审计输出逐类盘点（机械，`albus/audit28/` 可复算）

| 类别 | 件数 | 处置 |
|---|---:|---|
| 编号审计件 `AUDIT<n>_*.md` | **22**（AUDIT6–AUDIT27） | 全部补 `VERDICT:` 机读行；8 件另补「总判补录」说明，不改写任何原结论 |
| 索引 `AUDIT_INDEX.md` | 1 | 抬头改「AUDIT6 → AUDIT28」；补 AUDIT28 行、`COMPANIONS:` 清单、台账 `loc` 口径 |
| 配套/派生产物 | **39** | `AUDIT17_CLOSURE.md` + 38 份 `W*_AUDIT / W*VERDICT / W*REVIEW`；**冻结件，逐字保留**，只在 `COMPANIONS:` 点名 |
| 结案台账 | 2 | `AUDIT_LEDGER.tsv`（AUDIT12 的 48 行）、`AUDIT_LEDGER_A24.tsv`（56 行）；门查重复 id 与状态枚举 |

⇒ 合计 **64** 份。`tools/audit_outputs.py` 每次收工校验「索引行 ↔ 编号件 VERDICT」、
「派生产物 ↔ COMPANIONS」、两本台账、以及撤回标记是否还在。

## 2 上网复核（不猜，逐条给官方页面）

| # | 审计输出原写法 | 官方核实 | 判定 |
|---|---|---|---|
| 1 | AUDIT26：「#31188 PR 内没有性能栏，17.2% 无法核实，只能写作者称」 | `api.github.com/repos/ggml-org/llama.cpp/pulls/31188`：`title=CUDA: fuse MoE gate/up matmuls and GLU in MMQ`，正文 `### Performance` 表（`llama-bench -ngl 999 -fa on -p 16384 -n 0 -b 2048 -ub 2048 -ctk f16 -ctv f16 -r 5`）：**DGX Spark Qwen3-30B-A3B Q4_K_M 2911.4→3410.8 tok/s = +17.2%**；**RTX 5090 12611.7→13330.3 = +5.7%**；perplexity 逐位相同。`created_at=2026-10-26`、`merged_at=updated_at=2026-10-28`（不是事后补写） | **误判，P0，已全链撤回**。正确口径：数字属实，但 CUDA + MoE 融合（需 gate/up 行交错布局），gfx906/HIP 不适用；`P391`/`R102` 的结论不变，理由换掉 |
| 2 | AUDIT26：「#22174 是关掉 stream-k 后双 3090 +9.67%（2597→2848）」 | PR `22174` title `cuda: disable MMQ stream-k by default for MoE`，正文逐字 2597.04→2848.26 (+9.67%)、单卡 −0.005%~+0.073%；`merged=false, state=closed` | **成立**；补一条：该 PR **未合并**，引用时别写成「上游已默认关」 |
| 3 | AUDIT26/方案：「#22298 用 fastdiv + tiling **取代** stream-k」 | PR `22298`（`CUDA: reduce MMQ stream-k overhead`, merged 2026-04-25）正文：用 `fastdiv` 预计算除法降开销，**仅当 tiling 的效率损失 ≤10% 时**才用 tiling 跳过 stream-k fixup | **需收紧**：不是无条件取代。方案 §6.5 W1005 块已改写；「约 17% 属另一处 2×4090 报道」本轮**未核到一手出处**，标「未复核」 |
| 4 | AUDIT23 A23-2：「官方 ROCm 10.1.0 = CK 1.2.0 / rocBLAS 5.5.0 / hipBLASLt 1.4.1 / HIP 7.14 / LLVM 23，2026-10-05 发布」 | AMD 官方 `rocm.docs.amd.com/.../compatibility-matrix.html` 与 release notes 逐项吻合，发布日 2026-10-05 | **成立，且更强**：官方 10.1.0 支持矩阵最老只到 gfx908(MI100)，**不含 gfx906** ⇒ A23-2「照官方装会让 `gfx906-rocblas-5.7.0.txt` 失效」的判断更硬 |
| 5 | AUDIT19：「读屋顶 884 GB/s = 86.3% 规格（1024）」 | AMD 官方 MI50 32GB 规格页：`Peak Memory Bandwidth 1 TB/s`、60 CU、FP32 **13.3** TFLOPS、FP16 26.5、TDP 300 W | **分母成立**；顺带发现 W1014 记的「FP32 13.4 TFLOPS」应为 13.3（差 0.1，属抄写误差，不改既有结论）；`sdot4 21.7–22.3 TOPS` 本轮仍未核到一手出处，维持 AUDIT27 的「未复核」标记 |

## 3 方案优化：从「2,300 行里找现行值」变成「一张导航表」

- **§0.2 本件怎么读**（新增，7 行）：现值只认 §0.1；下一步只认 §0.1 唯一队列；条目定义在 §6.2；
  回写块查 §6.5.0；退役数字查附录 A；未结项查 `PROGRESS.tsv`；引用写小节名不写行号。
- **§6.5.0 回写块目录**（新增，机械生成）：26 个回写块逐块一行，取块首非空句作摘要；
  `tools/plan_single_source.py` 会在新增块而没同步目录时 FAIL。
- **§6.5 抬头横幅**：明写「本节从这一行起全是历史记录；『唯一排序处』是 2026-10-31 的旧说法」；
  并把 4 处非引用块的 `队列第 1 序 / 队列首位是 / 当前按 §6.5 顶部` 改成带日期的历史快照。
- **指针**：活文档里的 6 个 `W832:<行号>` 全换成 `W832 §0.1 / §6.2 R101 / §6.6` 等小节名；
  `AUDIT_LEDGER.tsv` 与记忆件里的旧行号按 A28-8 冻结保留，只在索引台账写明「`loc` 列是 2026-10-31 快照」。
- **数字副本**：`1.57×` 出现 40 次、`832` 15 次、`5e63174d` 5 次 —— 这些大多带轮次与证据件，
  属合法历史记录；本轮**不删历史**，只把「唯一现值」的判定收进 §0.1 并由 `audit_scope §D` /
  `plan_single_source §5` 双门校验分母与队列。

## 4 新门与复算

| 门 | 判据 |
|---|---|
| `tools/audit_outputs.py` | 22+1 件编号审计的 `VERDICT` 必须等于索引 P 列；39 件派生产物必须在 `COMPANIONS`；两本台账无重复 id / 状态合法；撤回结论不得写成现行事实（负向自测 4/4） |
| `tools/plan_single_source.py` | 唯一队列恰好 1 行且在 §0.1；§0.2 + §6.5.0 存在且目录覆盖全部回写块；历史排期声明必须是引用块或带历史标记；活文档禁 `W832:<行号>`；§0.1 分母 = `PROGRESS.tsv`（负向自测 4/4） |
| `tools/audit_index.py` | 合计 = 逐行和、边界由覆盖表派生（AUDIT27 立） |
| `tools/audit_scope.py` | 审计债 / 废止门 / 缺报告 / 分母队列（AUDIT27 立） |

```bash
python tools/audit_outputs.py --self-test
python tools/plan_single_source.py --self-test
python tools/audit_outputs.py && python tools/plan_single_source.py
python albus/w1002/round_close.py --report albus/w1033/reply.md --post
```

**过程留痕**：本轮一次 `io.open(p,"w").write(re.sub(...))` 在同一表达式里先截断文件、后因闭包作用域报错，把 `AUDIT24_W900_W951.md` 写成 0 字节。已由本轮开工前的 `*.bak_a28_20261107_015655` 逐字恢复，并重放 VERDICT 行与指针替换两处改动；`AUDIT_OUTPUTS` 与 `ROUND_CLOSE` 全绿后才继续。这正是本项目铁律「写文件禁同式内 read+open」的反例，登记在此以免下轮重复。

## 5 未结（明确边界，不造新号）

- `P392` 的 prefill-only LOGPOS 数值门仍未跑（要停生产 10–15 min，**未经机主点头不执行**）。
- `sdot4/sdot8` 的 TOPS 数据、「约 17% 的 2×4090 报道」本轮未核到一手出处，标「未复核」，不进判据。
- 冻结件（`W986_PLAN_V3.md`、`AUDIT_LEDGER.tsv`、记忆件）仍留旧口径，属**有意保留的历史证据**；
  需要现行口径一律走 §0.2 导航。
- AUDIT19 的 884 GB/s 只适用大块连续读（AUDIT22 已限定），本轮的 AMD 官方 1 TB/s 是**峰值规格**，
  两者不是同一个分母，不要拿着 1024 去重算 HC/GDN 的占比。

## 6 分母

整改前 **342 / 260 / 76.0%**；本件新增 `P401`–`P404`（4 条全结）⇒ **346 / 264 / 76.3%**。
生产：`strata-0.1.57-001` / config `53ac61e0…` / 容器 `2d765942e041` / `restarts=0`，全程只读。
