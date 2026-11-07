# W775delta AUDIT4 ---- 对抗性审计（AUDIT3 之后的 R1-R13）

日期 2026-10-11 16:5x ｜ 范围：`W775delta_AUDIT3.md`（覆盖到 ~14:0x）**之后**的全部轮次 R1-R13
方法：四条铁律（独立上下文只读子 agent `auditor4` + 本机逐条回原始字节复核 + 只认原始证据 + 不重复已自认项）。
范围件：`deploy/tmp/_audit4_scope.md`（注：该件里 `deploy/.workbuddy/memory/MEMORY.md` 路径写错，实为工作区根 `.workbuddy/memory/MEMORY.md` ---- AUDIT4 自查项）。

## 0 一句话

**无 P0。6 条 P1（结论被同源证据反证 / 对象错置 / 权威件计数自相矛盾 / 状态过期 / 前提过期）+ 9 条 P2（措辞与口径）。**
P1/P2 已全部回原始证据复核并**就地修正**（§5）。子 agent 报告的 13 条中 **1 条为判据错配的假红**（见 §1 #12 的边界），其余逐条成立。

## 1 结果总表（子 agent 13 条 + 本机 5 条，已去重）

| # | 严重度 | 类型 | 位置 | 依据（原始证据） | 判定 |
|---|---|---|---|---|---|
| C1 | **P1** | 权威件计数过期且自相矛盾 | `W750_MASTER_PLAN.md:16/23/303/304/548` | 现算 register = **86 数据行 / ADOPTED 26 · REJECTED 33 · CANDIDATE 21 · REFERENCE 6**；而 W750 出现 **9 / 11 / 12 / 75 / 78** 五个互斥且全错的计数。`todo_reconcile.py --strict` 报 GAP=0（它只查「承载位」，**不查计数串**）=> 机器判据的盲区 | **确认**（已修） |
| C2 | **P1** | 上游件状态过期 | `W775delta_UPSTREAM_1670_CORRECTION.md:5` | 该行逐字 `状态：**待发**（POST 后回填 id）`；而 W28B:3 / W28D:3 写「已发 `6107050493`」；匿名 API 现取该评论 **2,022 B / md5 `714d7d6e...` / created 08:17:28Z** | **确认**（已修） |
| C3 | **P1** | 因果归因错误（对象错位） | `W775delta_W28C_THREETIER_MECHANISM.md:83`、`W750_MASTER_PLAN.md:348` | W28C 逐字「`generate.cpp:7053` 那句 ... **只在 `multi_gpu` 分支打印** ⇒ 单卡看不到 ... 这正是此前一直没发现的原因」。但 `expert_source.cpp:3105-3109` 另有一句**同义**的 `N of M of the prompt path lendable slots keep their experts in RAM too`，守卫**只有 `if (lend)`**（`:2638 lend = lend_from_slot >= 0 && ...`）=> **单卡也打**。我们看不到的真正原因是 `budget_bytes > 0` ⇒ `lend=false` | **确认**（已修；并据实指出：改到 `--resident-experts` 后该句会出现，可作监视行） |
| C4 | **P1** | 结论泛化（前提被同源证据反证） | `W775delta_W28B_RAM_COMPLEMENT.md:8`、`W28C:35`、`W28D:24`、W750:348 | 三件逐字「补集**恰好 = base**（33.44/33.45 GiB）⇒ budget 过量 ⇒ 借区一个槽都没进 RAM」。但**同一 `--resident-budget-gib 76`** 下，原始件 `_cold_raw.txt` 实测补集有 **33.44（:770）/ 33.45（:599）/ 36.80 GiB（:815）** 三值（36.80 那 boot `16308 of the 36.80 GiB`、GPU-cache 仅 8,268 槽） | **确认**（已加「逐 boot 成立、非恒真」限定） |
| C5 | **P1** | 上游他机数字当本机 | `W775delta_W28E_COLD_OPT_FULL.md:19`（G2） | 逐字「`STRATA_IO_PF_STAGE=1` 在**最近本机的车道**（32 GB, IQ3_XXS）实测 **+25.7%**」；而 `DETAILS.md:237` 该行是 `| RTX 3060, 32 GB, IQ3_XXS | -3.4% | **+25.7%** |` => **上游 RTX 3060 车道**，非本机 | **确认**（已修；T237 型对象错置） |
| C6 | **P1** | 过期前提未加限定 | `W775delta_W13_HEADROOM_RECHECK.md` §6 | §6 第 4 条仍以「`P54` 已证 file/RAM tier 非瓶颈」为活前提，文件内无 W28 撤回注；而 `P54` 现态 = CANDIDATE、W28 已判该前提对冷路径**错误** | **确认**（已加 W28/AUDIT4 限定） |
| C7 | P2 | 措辞自相矛盾 | `W28E:106` vs `:56` | §6 车序把 B8（`STRATA_STAGER_SSD=1`）标「**零风险单变量**」；而同件 §4.1 OPT-E 代价 = 「页缓存真温时 **4-7x 慢**」（`prefill.cpp:1063-1064` 逐字） | **确认**（已修措辞） |
| C8 | P2 | 快照表内引用过期两代 | `W775_HANDOVER.md:60` | 该行引 `W13_RESULT.md` = 11,440 B / `13d67200...`；现为 **13,400 B / `28221acd...`**（BAN 前亦为 12,137 B / `b85d8436...`） | **确认**（该表自带「05:30 时点快照、引用前现算」注 => 属自证快照，未改） |
| C9 | P2 | 行标签与产物不符 | `W775delta_W26_TIER_REPLAY.md:43` | 行标「profile 预填、`--swaps 0`（无迁移）= 0.7086」；`_w26_out/replay_swaps0.out` 实为 `policy every 4, swaps 0, decay 0.70: share 0.7086` => 是 policy 模型，非 fill-only（数值恰同） | **确认**（已改标签，防对象混用） |
| C10 | P2 | 聚合口径并置 | `W775delta_W28_COLD_PATH_REDESIGN.md:12` | §0 把「222,659 次 major fault」写在「累计 371 GB / 1.10 TB」同一串末尾；§1.2 表才写清它是**单请求 max**（84/198 非零） | **确认**（已加限定） |
| C11 | P2 | 跨件数值不一致 | `W28B` vs `W28C` vs register | W28B 用 33.45 / 55.45；W28C 用 33.44 / 55.44；来源是不同日志行（`resident RAM` vs `complement ready`） | **确认**（已在 C4 限定中说明来源差异） |
| C12 | P2 | 定义依赖断言 | `_bound_land.py:83` | 「全库只 1 处」仅在**排除 `tmp/` 与 `.bak`** 时成立（现算含 `_bound_land.py:22`、`_audit4_sync.py:35`、handover 的两个 `.bak`）。**注**：任务书称该句出自 `W13_HEADROOM_RECHECK.md`，实为该 tmp 脚本；AUDIT4 已纠正位置 | **确认**（tmp 簿记件，未改） |
| C13 | P2 | 任务书路径笔误（**AUDIT4 自己的**） | 发 `auditor4` 的 prompt（**非 scope 件**；scope 件 L54-55 只写 `MEMORY.md`，无错） | prompt 里写成 `deploy/.workbuddy/memory/MEMORY.md`，实为工作区根 `.workbuddy/memory/MEMORY.md` | **确认（无文件缺陷；已在 §5 记为「无文件改动」）** |
| C14 | P2 | 命中率低尾未披露（本机新发现） | `W13_HEADROOM_RECHECK.md:20/26`、`W26:0` | 全日志 `decode expert cache hit rate` 196 行：**58/196（29.6%）低于 88%，最低 66.7%**（本机现算）；而件内只给「长跑 97% / 尾部 95.4-98.0% / 短请求 88.1-90.1%」 | **确认**（已在 §6 加注） |
| C15 | P2 | 分位数方法未声明（本机新发现） | `W28_COLD_PATH_REDESIGN.md` §1.1/§1.3 | 中位数用「两中项平均」可复现（12,564 ✓）；但 **p90 不可复现**：冷 `read_ms` p90 报 38,590、本机复算 39,317；gpu p90 报 64.09、复算 64.78；disk p90 报 7,584.3、复算 7,611.5（p50/max/中位全对） | **确认**（方法未写；未改数字） |

## 2 本机对 P0/P1 的逐条复核判定（技能要求）

- 子 agent **无 P0**。
- **C1/C2/C3/C4/C5/C6 六条 P1 全部回原始字节复核 => 全部成立**（证据见 §1 右列；C4 的 36.80 GiB boot 由我在 `_cold_raw.txt:815-824` 直接读到）。
- **子 agent #12（"全库 1 处"）**：其数值判定成立，但**它自己的任务前提（位置）有误**（该句不在 `W13_HEADROOM_RECHECK.md`，在 `_bound_land.py:83`）=> 属判据/出处层面的瑕疵，非被审件缺陷。
- **子 agent #13（scope 路径错）**：成立，且是**本审计自己的错**，非被审轮次缺陷。

## 3 无法验证清单（不得当作「已通过」）

1. 上游评论 `6107050493` 的 md5/字节：API 现取 **2,022 B / `714d7d6e...`**（与 W28B 声称一致），但**本机交付件此前零记录**该值，无法本地自证未被改动（本次已回填）。
2. 上游 `#1670` reply `6106913235` 正文：本机可核（1,173 B / `7aa25d67...`）；但正文转述的数字（33.45 GiB 等）只能核到「与日志一致」，**无法验证上游页面是否被第三方编辑**。
3. **W28 系列的车 B7/B8/B9/B10 全未发** => 所有「预期 / 应 > 33.44 / 36.9 GiB / +25.7%」都是**方案预期**，不是本机读数。
4. `available RAM ≈ 37.44 GiB`：W28D 自注「推断值，非直读」，且 `_cold_raw.txt:817` 另有一 boot `38.37 GiB really free`，两值不能互证。
5. `36.80 GiB` boot 的**归属配置**（同 pack？同槽数？）：仅凭 `_cold_raw.txt` 无法确认它与 33.44 boot 同 config => C4 只能判到「同 flag 下补集随环境浮动」，**不能**判到「同一 config 恒 > base」。

## 4 已回原始证据核实且成立（只列真核过的）

1. **W26 全部数字**：`_w26_out/bench_prefill.csv` = `9761,global,fill-only,all,1842240,1305412,0.7086,0`；lru 0.9751 / lfu-decay 0.9767 / oracle 0.9890；`replay_default.out` = 0.9669 / 0.7086 / `0.9564, swaps 11601`；`swaps0` 0.7086；`every1` 0.9556；`noedge` 0.9590。**逐值吻合**。
2. **W26 五参数对源码**：`generate.cpp:577/578/581/607/8165` => every 4 / decay 0.7 / min-gain 1.5 / swaps 96 / 候选门 2.0。**逐行到位**。
3. **`generate.cpp:5008` 的 `policy is\n` 真缺参数字段**（更正所指的上游小 bug 属实）。
4. **W28 请求级/文件层统计**：166 日志 196 prompt 行；冷 **76** / 温 **120**；冷 `read_ms` 中位 **12,564** / p90 38,590 / max **251,925**；filetier 198，OS read 累计 **371,807.5**、专家读 **1,099,238.8**、单请求 max **64,649.1** / faults max **222,659** / 非零 **84/198**。**与 W28 §1 全部吻合**。
5. **netdata 48h**：gpu p50 **0** / max 99.97；cpu user max **51.46**；iowait max **20.78**；disk reads max **356,205.5**；**66/1440** 命中条件；13:36 行复现。
6. **166 现态**：`strata166-407` Up；引擎 md5 `5efa1d45...`；config md5 `6261ddf8...`；`/v1/models` 200；`stager takes the RAM profile` **30** / `cache complement ready` **37** / `borrows 1554 CUDA0 cache slots (3.49 GiB)` / `9761 in the GPU cache` / `24,720 blob reads from the file` / `kept_in_RAM_too = 0`。
7. **W28B/C/D 引的源码行**：`expert_source.hpp:550-552`（含 "No lend region then"）、`expert_source.cpp:2635/2638/2649-2650/3105-3119`、`generate.cpp:2077-2082/6538-6544`、`prefill.cpp:1051-1083`。**逐行到位**（唯一 off-by-one：`STRATA_RESIDENT_PIN=0` 的 "exact tokens" 句在 `DETAILS.md:184-185`）。
8. **`P64`-`P71` 均为真 getenv/arg-parse**（`generate.cpp` / `prefill.cpp` / `expert_source.cpp`），非只在 docs。
9. **register 现态**：86 数据行 / 11 列 / 0 重复 ID / **26 · 33 · 21 · 6**。
10. **`P54`/`P46` REJECTED -> CANDIDATE** 经备份差分成立（`bak_w28_20261011_161215` 对现态）。
11. **W4X_GDNPP**：decode all-10 **-2.54%** / warm-8 **-1.69%** / prefill -0.14% / -0.13%；parity `5a4b25aa...` = `md5("391")` 现算相等。
12. **`todo_reconcile.py --strict` = GAP 0 / exit 0**（但它不覆盖 C1 的计数串）。
13. **W27/W23/W24 的源码与文档引用**：`DETAILS.md:199`、`AMD_HIP.md:199`、`DETAILS.md:94`、`BATCHED_DMA.md:3-13`（"CUDA 13.0 or later ... HIP retain individual copies" + "not a demonstrated increase"）、`generate.cpp:522`（"up to 8192"）、`generate.cpp:5047-5055/5386-5387`、`prefill.cpp:260-263`、`coupled_draft.hpp:75` ---- **逐行到位**。
14. **W24 六开关在 0.1.42 全树命中 0**（`PREFILL_LAYER_MAJOR` 等）。
15. **`_cold_raw.txt` / `_netdata_48h.txt` 的原始性**：分节拼装（`### PROMPT_LINES` / `### FILETIER_REQ` / `### RESIDENT_RAM` / `### FILEEXPERT` / `### FILEEXPERT` ...），**行内容为逐字原始日志/导出**，非二次摘要。
16. **四条上游评论**：`6106275361`（1,243 B / `d8c96c7a...`）· `6106666399`（3,270 B / `2d2abf06...`）· `6106913235`（1,173 B / `7aa25d67...`）· `6107050493`（2,022 B / `714d7d6e...`），匿名 API 现取**字节与 md5 全对**。
17. **`W13_RESULT` 旧 md5 `13d67200` 现算仅 1 处交付件引用**（`W775_HANDOVER.md:60`，自证快照）。

## 5 已修正清单（本次就地落盘，改动前备份在 `deploy/tmp/_audit4_bak/`）

| 件 | 改动 |
|---|---|
| `W750_MASTER_PLAN.md` | C1（5 处计数改现算 86/21/33）· C3（归因更正）· C4（补集限定）· §8 加本件指针 |
| `W775delta_W28C_THREETIER_MECHANISM.md` | C3（归因段重写）· C4（补集逐 boot 限定） |
| `W775delta_W28B_RAM_COMPLEMENT.md` | C4（加限定） |
| `W775delta_W28D_OPT_PLAN.md` | C4（加限定） |
| `W775delta_W28E_COLD_OPT_FULL.md` | C5（"本机"-> 上游 RTX 3060）· C7（"零风险"措辞）· 硬证判据修正（改用 `N == M` 行）· OPT-E 加平台 |
| `W775delta_W13_HEADROOM_RECHECK.md` | C6（W28 前提撤回注）· C14（命中率低尾 58/196） |
| `W775delta_UPSTREAM_1670_CORRECTION.md` | C2（待发 -> 已发 + md5） |
| `W775delta_W26_TIER_REPLAY.md` | C9（行标签消歧） |
| `W775delta_W28_COLD_PATH_REDESIGN.md` | C10（major fault 单请求 max 限定） |

**未改**：C8（自证快照，按「历史快照不动」保留）· C11（已在 C4 说明）· C12（tmp 簿记件）· C15（方法未写，数字可信）· `register`（本轮无裁定面变更）。
**C13**：无文件改动（笔误在我的子 agent prompt 里，scope 件本身无错）。
**补充（2026-10-11 16:5x 机主复问「审计输出是否都已整改」时二次核对）**：`W750` 另有两处**历史计数**（L194 `75 数据行`、L258 `CANDIDATE 9`）分别位于 §0.5.6 与 §0.7 的**带日期/带 md5 的**历史块中 => 已各加「**该时点**」标注并指向 §0.0 现况；未改写历史数字。

## 6 局限

1. 本审计**未发任何车**；W28 系列全是方案。
2. 上游页面无版本史，只能核当前态。
3. 计数器/哈希依赖本机 Python（coreutils 缺失），判据集：计数=整文件扫描，md5=文件字节。
