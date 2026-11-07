# W775delta AUDIT5 ---- 对抗性审计（AUDIT4 之后的 R14-R22）

日期 2026-10-11 19:xx ｜ 工作区 `D:/workbuddy_space/strata_ws/`
范围：`W775delta_AUDIT4.md`（覆盖 R1-R13，落盘 ~16:57）**之后**的全部轮次 R14-R22（范围件 `deploy/tmp/_audit5_scope.md`）。
方法：四条铁律（**独立只读子 agent 已派（`Explore-1`，工具集无 Write/Edit），但在本窗口内未返回结论 => 本波的独立复核由「四组车原始日志/cfg/parity/speed JSON + 166 生产日志整份（3,771 行）全部拉回本机 + 离线自建请求级解析器复算 + netdata 历史 API 按窗重取」承担**，见 §6.5；另加本机逐条回原始字节复核 + 只认原始证据 + 不重复已自认项）。
**本波首次把四组车的原始日志/JSON 整份拉回本机**（`deploy/tmp/_audit5_ev/`，74 件）后离线复核，并**把 166 生产日志（3,771 行）整份拉回**做请求级对账。

## 0 一句话

**3 条 P1（一条数字绑错请求 · 一条 netdata 口径失真且旁证缺失 · 一条入口件自相矛盾）+ 5 条 P2（分位数与口径未声明）。**
**B7 的核心硬证（N==M / 补集 36.93 / B 臂 10/10 files 0 blobs / −2.50% 区间不重叠 / parity 5/5 / register 与 cfg md5 / verify PASS=27）经本机逐条复算，全部成立。**

## 1 结果总表

| # | 严重度 | 类型 | 位置 | 依据（原始证据） | 后果 |
|---|---|---|---|---|---|
| **A1** | **P1** | 数字绑错请求（**传播 6 处，含 1 处已发上游**） | `W775delta_W4X_RES_RESULT.md` §8 旁证 / §11 B 段 / §9.1 / §10.1；`W775delta_W28_COLD_PATH_REDESIGN.md` §1.2 表 max 列 + 其下「逐字行」+ §1.3 互证段；`W775delta_W28C_THREETIER_MECHANISM.md:74`；`W775delta_W28E_COLD_OPT_FULL.md:31`；`W775delta_UPSTREAM_1670_CORRECTION.md:28`（**已发** comment `6107050493`） | 生产日志 `_audit5_ev/strata-huihui-ud-iq4_xs.log`：`L2834` = `the OS read 64649.1 MB from storage (1406 major faults) for 23613.1 MB`（**60-token 首请求** `L2829`）；`L2842` = `27429.5 MB (222659 major faults) for 38258.9 MB`（64,026-token `L2837`）；`L2569` 自己的 = `3375.7 MB (0 major faults) for 79756.2 MB`（110,793-token） | 三条不同请求的三个 max 被拼成一条并归给 64K/110K 请求。`W28_COLD_PATH_REDESIGN` §1.2 下方那句**自称「逐字行」实为三请求拼接**（非逐字）；AUDIT4 §4.4 只复了累计值与各 max 各自成立，**未查拼接**。上行评论同错 => 已起草 follow-up |
| **A2** | **P1** | 遥测口径失真 + 旁证未落盘 | `W4X_RES_RESULT.md` §8 第三条；`W750_MASTER_PLAN.md:241`(§0.6) 同源 | (1) 采集脚本 `deploy/tmp/_b7_nd.py`(17:51) 与 `_b7_long.py`(17:47) **只 `print` 到终端，全库无落盘产物**（`grep -rl 'gpu util pct'` 仅命中脚本自身）。(2) 本机按同参数复现（`after=-420&points=70&group=average`，窗口止 17:52）得 `disk.sda reads max=48602.4 KiB/s`(≈47.5 MB/s) · `cpu.user max=43.9` · `cpu.iowait max=7.6` —— **与报告 48 / 43.9 / 7.6 逐字吻合**，证明四数字即该次降采样输出。(3) **但同窗 `group=max`（真峰）= `disk.sda reads 201635.7 KiB/s ≈ 197 MB/s`、`cpu.iowait 31.6%`、`cpu.user 52.5%`**；(4) gpu 均值复算 = **70.1%**（报告写 79%）；(5) "改前 356 MB/s" 是 **48h 真实峰**（`disk.sda` 48h `group=max` 复算 **555,139 KiB/s**）=> **真峰 vs 降采样均值峰，口径不可比** | 「原症状不复现」的**硬盘读满**与 **CPU 满载**两条证据不成立：同口径下只降约 1.8x（非 7x）；`cpu.user` 改前 48h max 51.46% ≈ 改后 52.5%（**没有变化**）。该发现经 `W750:241` 二次传播 |
| **A3** | **P1** | 入口件同文件自相矛盾（且是待办项） | `SESSION_KICKOFF.md:12` vs `:42` | L12 逐字「`.workbuddy/memory/MEMORY.md`（长期记忆，**3,000 字符注入窗**，现 **2,898 chars 在窗内**）」；L42 逐字「**`MEMORY.md` 超窗**（现 **4,2xx B** > 3,000 字符）=> 开工第一件事应走 `routek-memory-slim` 技能压回窗内」。实测 `MEMORY.md` = **2,900 chars**（在窗内）。W752 的同步脚本 `_b7_sync.py:55` **只改了 L12** | 同文件跨节互斥（清单 #18）；且 L42 是**待办项** => 会驱动下一会话对已达标的件做无用压缩（且技能入口本身会 fail-closed 拦下，白耗一轮） |
| **A4** | P2 | 分位数方法未声明 | `W775delta_W4X_STG_RESULT.md` §2 | 表内 `file-tier OS 读 MB/请求 med` 报 **18.2 / 13.8**；本机复算标准中位 = **17.2 / 13.05**（`upper median` 才是 18.2/13.8）。冷 `read_ms med` 报 25,419；标准中位 25,417（同法）。**与 AUDIT4 的 C15「分位数方法未声明」同族** | 数值差异小、不改结论；但同一批车里只有这一件给分位数却未写方法，读者无法复算 |
| **A5** | P2 | 「主口径」跨件不一致 | `W4X_STG_RESULT.md` §2 vs `W4X_RES_RESULT.md` §2 | B8 的「冷 `read_ms`（主口径）mean = 25,735 / 25,804」是**全 10 点（含每臂 r0 冷启动点）**；B7 的「冷 `read_ms`（去 r0，主口径）」是 **8 点** | 两车的"主口径"分别用全点/去 r0；若把两车并列读会低估 B8 的 r0 污染（B8 去 r0 后 = 25,410 / 25,466，+0.22%，方向不变） |
| **A6** | P2 | 算式口径混用（与同件 §10.1 的修正未同步） | `W4X_RES_RESULT.md` §9.1 | `files 1554 blobs **52981.0 MB** read`（`_w4z_resL_blk2.log`）是 **since the start 累计**（= 起机 23613.1 + 本请求 29367.9）；§9.1 却用 `52,981 MB / 108 s ≈ 490 MB/s`（**累计量 ÷ 单请求时长**）。同件 §10.1 已改用**本请求口径**（`29,369.5 MB` vs OS `1,873.7 MB`） | 同一结论（页缓存温）两处口径不同；§10.1 修正后 §9.1 未同步 |
| **A7** | P2 | 数字精度 | `W4X_RES_RESULT.md` §11 B 表格 #2 | 表格写 `~127.7 s`；日志实测该请求 = `read in 127539 ms`（**127.5 s**）。#1 = 127,839 [OK] · #3 = 127,699 [OK] | 用 `~` 掩盖了 0.2 s 偏差；不影响结论 |
| **A8** | P2 | 论证不成立（同 A2 源） | `W4X_RES_RESULT.md` §10.3；`W750:241` | 称「`B10` 动机弱化：生产冷探针 `cpu.user` 峰仅 **43.9%** => CPU 不再满载」。该 43.9% 是**降采样均值序列的 max**；真峰 52.5%，且改前 48h `cpu.user max = 51.46%` => 改前改后**没有变化** | `B10` 降级的方向可保留（CPU 从未真正"满载"），但**不能**用这组数字作论据 |

## 2 本机对 P1 的逐条复核判定

- A1：**成立**。三处 file tier 行与三个 prompt 行逐行取自拉回的生产日志（`_audit5_ev/strata-huihui-ud-iq4_xs.log`），可 `sed -n '2828,2843p'` 复现。
- A2：**成立**。四数字已用**同参数**（`after=-420&points=70&group=average`）复现出三个逐字吻合值 => 来源确定；再用 `group=max` 得真峰，口径差异确定。**采集脚本无落盘**为独立事实。
- A3：**成立**。`SESSION_KICKOFF.md` 4150 B，两行逐字见右列；`MEMORY.md` 实测 2,900 chars。

## 3 无法验证清单（不得当作"已通过"）

1. **`gpu 均值 79%`**：本机在同参数窗（止 17:52）复算 = **70.1%**，止 17:51 = 83.2%。**无法定位到恰好 79% 的窗口** => 该数字**无出处**（除非承认它是四舍五入/换窗口）。
2. **`disk 读峰 48 MB/s`**：可复现为 `48602.4 KiB/s`（47.5），但**无落盘**，且与"峰"的语义不符。
3. `_b7_long.py` 与 `_b7_nd.py` 的**实际运行时刻**：只能由 mtime（17:47 / 17:51）与脚本内 `after=-420` 推断；无运行日志。
4. 上游 `#1670`/`#1923`/`#1926` 的**页面是否被第三方编辑**：本波未复拉（上一波已核字节+md5）。
5. `B7-long`/`cold` 的 blk3/blk4 speed JSON 缺 engine 行（`mk(src,tag)` bug 的后果）—— 结果件已自纠并声明"从 blk1/blk2 log 补回"；本机已回 `_w4z_resL_blk1.log` / `_w4z_resL_blk2.log` 逐值核**补回值正确**（见 §4.6）。

## 4 已回原始证据核实且成立（只列真核过的）

1. **四组车单变量**（`*_cfg_blk*.json` 逐 blk 比对）：stg A/B 只差 `env STRATA_STAGER_SSD`；res A/B 差 `--resident-budget-gib 76` ↔ `--resident-experts` + `env HEADROOM`；resL/cold 的 **A 臂逐字等于现役 config、B 臂逐字等于 `bak_b7_20261011_173722`**（本机 JSON 逐字段比较）。**无隐式开关**。
2. **B7 硬证**（`_w4y_res_blk*.log`）：`allocating 36.93` + `ready: resident 36.93, pinned 36.93` + `1554 of the prompt path's 1554 lendable slots keep their experts in RAM too`（**N==M**）；**B 臂 blk2/blk3 的 `files N blobs` 全为 0（各 6 个采样点，10/10 run）**；A 臂 blk1/blk4 = `0,1554,3108,4662,6216,7770`（每 run +1554）。
3. **B7 冷 read_ms**（`_w4y_res_speed_blk*.json` 的 `engine_prompt_line` 逐 run 提取，去每臂 r0）：A(n=8) = **25,416.5**（`min 25,378 / max 25,455`）；B(n=8) = **24,780.5**（`min 24,763 / max 24,810`）=> **−2.50%**，**区间不重叠**（间距 568 ms ≫ 臂内宽 77/47 ms）=> 报告的三处数字**逐值吻合**。
4. **B8 冷 read_ms**：A 全 10 点 = **25,735.1** / B = **25,803.7** => **+0.27%** [OK]（报告数字对；口径问题见 A5）。B8 两臂 `major faults = 0` [OK]；OS 读 mean 122.4 / 119.4（−2.49%）[OK]。
5. **resL / cold**：resL A = (107218+106123+107219+106276)/4 = **106,709** / B = (108246+107019+108224+108301)/4 = **107,947.5**（报告 107,948 [OK]）=> B 慢 **1.16%** [OK]；cold A = (107567+106482+107670+106334)/4 = **107,013.2** / B = (108579+108542+108574+107250)/4 = **108,236.2** [OK] => **1.14%** [OK]；两车区间与报告一致 [OK]。
6. **resL 补回值**：`_w4z_resL_blk1.log` 的 `read in` 序列 = `652/107218/106123/679/107219/106276`；`_w4z_resL_blk2.log` = `670/108246/107019/672/108224/108301` => 报告 §9.1 表格**逐值正确**（blk3 从 blk2.log、blk4 从 blk1.log 补回 [OK]）；`files-blobs` 序列亦证实 log 名复用的自纠描述 [OK]。
7. **cold 的"正确证据"**：`_w4z2_cold_speed_blk2_r0.json` 的 io 行逐字 `the OS read 1873.7 MB from storage (42 major faults) for 29369.5 MB of expert reads` => 报告 §10.1 的 29,369.5 / 1,873.7 / 42 **逐字吻合**；93.6% ≈ "约 94%" [OK]。
8. **生产请求级**（拉回日志 3,771 行，自建解析器）：idx196-205 即 R18/R21 的全部依据 —— 5 次 16K 冷读（`blob reads = 0`、`files 0 blobs`、温读 24763/24696/24762/24758 [OK]）；长冷 49,720/49,721（`105606 / 106108 ms`，470.8/468.6 tok/s [OK]）；三条 60K（`127839 / 127539 / 127699 ms`，OS 读 `6687.5 / 8.1 / 5.7 MB`）=> §8/§11 的这些数字**全部正确**。
9. **W752 的 575.1 MB 判据**：idx196 = `OS read 575.1 MB (7 major faults)`（普通重启后首条）vs idx203 = `6687.5 MB`（drop_caches 后首条）=> 「不做启动预热」的判据**成立** [OK]。
10. **账本**：register 86 数据行 / **27 ADOPTED · 34 REJECTED · 19 CANDIDATE · 6 REFERENCE** [OK]；`P09 REJECTED` / `P66 ADOPTED` / `P65 ADOPTED` / `P67 CANDIDATE` [OK]；交叉引用已改 `--resident-experts(**P09 已废**)` [OK]；`generated/…json` = **1,393 B / `ff8cb97379f0bdbe76ee555da6d8729c`** [OK]；`_verify_20261011_1900.txt` **PASS=27 FAIL=0** [OK]；`MEMORY.md` **2,900 chars**（窗内）[OK]；`W750:24` 生产行含新 cfg md5 [OK]；`W775_HANDOVER.md` §2.2 已加现况指针 [OK]；`W775delta_EXT_VALUE_REGISTER.md:11-12` 触发条件 + "17:37 已兑现" [OK]；`W750:194/258` 已加"该时点"标注 [OK]。
11. **parity**：四组车全部 `= 391`（`substr(str(md5(bytes("391"))),0,16)` 现算）[OK]。
12. **B9 作废 / B10 降级的方向**：B9 靶（file 层专家读）在稳态确为 `0.0 MB`（idx197-205 除首条外全 0）=> 靶归零 [OK]（但见 A2 对"论据"的更正）。

## 5 已修正清单（本次就地落盘；改动前备份 `deploy/tmp/_audit5_bak/`）

| 件 | 改动 | 落盘脚本 |
|---|---|---|
| `W775delta_W4X_RES_RESULT.md` | **A1**（§8 旁证段的 64,649 MB 改为该请求真实值 27,429.5 MB + 标注另一条 60-token 请求；§11 B 段同理改为 3,375.7 MB）· **A2**（§8 第三条重写：netdata 来源与参数、未落盘声明、"峰"的口径更正为降采样均值峰、补真峰 197 MB/s、撤回「CPU 满载不复现」；§10.3 同理）· **A6**（§9.1 的 52,981 改标为 `since the start` 累计，撤掉「÷108 s ≈ 490 MB/s」这条算式，改引 §10.1 的本请求口径）· **A7**（§11 表格 #2/#3 写实值） | `tmp/_audit5_apply.py`(A1) · `_audit5_apply2.py`(A2/A6/A7) |
| `W775delta_W4X_STG_RESULT.md` | **A4**（§2 表下加注：`med`=上中位数、标准中位复算值）· **A5**（注明「主口径」= 全 10 点含 r0，与 B7 车的「去 r0」口径不同；补去 r0 复算 +0.22%） | `tmp/_audit5_apply2.py` |
| `SESSION_KICKOFF.md` | **A3**（TODOLIST 第 5 条 `MEMORY.md` 超窗的**过期状态**划删 + 更正注；与同件第 2 条 2,898 chars 对齐） | `tmp/_audit5_apply2.py` |
| `W750_MASTER_PLAN.md` | **A2 传播面**（§0.6 W28E-B7 行：79%->70.1%、48 MB/s 标注为降采样均值峰 + 真峰 197、口径不可比；`B10` 降级理由的 43.9% 撤回） | `tmp/_audit5_apply3.py` |

### 5.1 A1 补遗（2026-10-11 19:2x，机主令「确认审计问题都整改」时对 `64,649` 做全库 grep）

发现 A1 的**传播面不止 §8/§11**，遂逐处同步（脚本 `tmp/_audit5_a1fix.py` / `_a1fix2.py` / `_a1fix3.py`，备份 `_audit5_bak/*.bakaudit5b`）：

| 件 | 位置 | 改动 |
|---|---|---|
| `W775delta_W4X_RES_RESULT.md` | §9.1 判据修正句 | 「改前 64,649 MB 真存储读」改标为**单请求 max**（60-token 首请求） |
| 同上 | §10.2 后的「生产上的大差」句 | 「改前**该请求**真存储读 64,649 MB」拆为**两条不同请求**（max OS 读 / max 冷读） |
| `W775delta_W28_COLD_PATH_REDESIGN.md` | §1.2 表下「逐字行」 | **原一句是三请求拼接（非逐字）** => 拆回**三行真实日志**并各标 `L` 号 |
| 同上 | §1.2 表下 | 加注：`max` 列三值分属三条不同请求 |
| 同上 | §1.3 互证段 | 「那条 110K 冷请求 OS 读 64,649 MB」改为它**自己**的 `3,375.7 MB`（并指出另两值归属） |
| `W775delta_W28C_THREETIER_MECHANISM.md` | :74 | 同上更正 |
| `W775delta_W28E_COLD_OPT_FULL.md` | :31 | 「64,649 MB / 222,659 faults」注明两值属不同请求 |
| `W775delta_UPSTREAM_1670_CORRECTION.md` | 尾部 | 加 **AUDIT5-A1 补遗注**：该括注**已发**，需 follow-up |
| `W775delta_UPSTREAM_1670_FOLLOWUP.md` | **新建** | **上游 follow-up 更正草稿（英文，待机主过目后发）** |

**BAN/CR 复验**：以上 6 件（含新建 follow-up）**CR=0、BAN delta <= 0**（`W28E` 因把 `U+2192` 换成 ASCII 而 delta = -1）。

**有意未改**：
- `W750` 内**带日期/带 md5 的历史块**中的旧 netdata 数字（若属历史快照，按「历史件逐字保留」不动）；本波只改 §0.6 当前态行。
- `W750:350`（§0 的 `W28` 行）里的「改前 48h 磁盘读峰 356 MB/s」= **改前**读数，方向正确，未动；但其采集参数未落盘（属 AUDIT4/R8 范围，本波仅在 §3 记为口径待齐）。
- `deploy/tmp/*` 下的临时脚本与 `_audit5_ev/` 原始证据：**不动**（证据件）。
- `.workbuddy/memory/2026-10-11.md`：**append-only**，不覆盖历史行；本波另追加一条 AUDIT5 记录。

## 6 局限

1. 本审计**未发任何车**，未改生产。
2. 遥测侧：netdata 为**时变量**，本机复算是"按时间窗重取"（可复现，但不等于同一次运行）—— 这正是 A2 的立论基础。
3. 日志侧：166 生产日志虽跨多次 boot，但**首行即 `strata-vision: model files loaded`**，说明其起点不是完整 boot；本波只按下标引用行号，未做 boot 分段归属以外的推断。
4. 计数器/哈希依赖本机 Python 3.13.12（coreutils 缺失）；判据集：计数=整文件扫描，md5=文件字节。
5. **独立子 agent 的状态（据实）**：`Explore-1` 于本波派出（prompt 含四组车 cfg/speed/log 的核验清单与 E/F/G/H 四组专项），**运行 10m39s 后仍无返回**，机主侧发「立即收敛交付」指令后仍无响应，遂取消（`TaskStop`）。**因此本波没有"第二个模型换立场"的产出**；替代保障是把**原始证据全量拉回本机离线复算**（这一步比读报告转述更强，A1 即由此发现）。**A1/A2/A3 三条 P1 全部由机主侧独立取证成立**，不依赖该子 agent。
