# W713 方案 ---- 在 W712 基础上优化（含 0.1.41 升级与"升级闸门"标准化）

> **已冻结（2026-10-31 17:4x）。方案权威改为 `deploy/W832_OPT_PLAN_V2.md`（§0.0）。本件仅作历史与证据，不再更新队列。**

> 写于 2026-10-08 22:1x CST。上游 `Niko1221/Strata`。
> 本件**取代** `W712_PLAN.md`（那份保留为 W712 波次的历史记录）。
> 升级实施与自证见 `W713_UPGRADE.md`（待写）。
> 本件 CR=0，不含禁用码位（U+21D2 / 2192 / 2014 / 2013 / 2026 / 2265 / 2264 / 2260 / 2212 / 00D7）。
> 所有性能读数一律 **Z0=off**；分辨力：预填 1.2-1.7% / 解码 9.5-15%。

---

## 0 一页速览：这次"优化"改了三件事

**当前状态（23:2x，含第二轮对抗性审计后修订）**：生产 = **`strata-gfx906:0.1.41` / 容器 `strata166-405`**（22:35 切换，中性已验）；**三路独立对抗性审计已完成两轮**（报告 `deploy/W713_AUDIT.md` 与 `deploy/W713_AUDIT2.md`）；**全量账见 §6**（已做 / 没做 / 重做 三张表，计数以 §6 各表标题为准）。

| # | 优化 | 依据 |
|---|---|---|
| **1** | **升级到 v0.1.41**（本方案第一优先） | 上游 2 小时前发布；且**我们的 PR #1396 已合并 => gfx906 补丁面归零**（实测 `patched=0 / verified=6`） |
| **2** | **把"升级闸门"标准化成脚本**（每次换引擎都跑，约 10 分钟） | W712 里"中性验证"是一次性人工编排；上游一周发 20 个 release，**必须可重复** |
| **3** | **新增一条候选旋钮 + 两条旧候选复活**（见 §2） | 0.1.41 的 #1353（RAM-resident prompt reader）、#1347（会话缓存淘汰修复）、#1454（省 320 MiB） |

**不变的铁律**：改参数只走 register -> `gen_config.py --write` -> 推 166 -> restart -> `verify_config.py` FAIL=0；
A/B 走 `cfg_A/cfg_B` 实验通道，**register 的值只有测量+采纳后才动**；register 是唯一真值。

---

## 1 v0.1.41 里与我们（gfx906 / 单卡 / Linux / HIP / 全专家驻 RAM / 262k 上下文）相关的条目

**(1) 补丁面归零（本次升级的实质变化）**

| 处 | 0.1.40.4 | **0.1.41** | 实证 |
|---|---|---|---|
| H5 `CMakeLists` q6_k 实例门 | 要打 | **上游已修** | 原始树第 1270 行 `if(STRATA_Q6K_EXPERTS OR STRATA_HIP_GFX906)`，含我们写的注释 |
| H6 `strata_hip.h` 补 `cudaEventBlockingSync` | 要打 | **上游已修** | 原始树第 52 行 `#define cudaEventBlockingSync hipEventBlockingSync` |
| H1-H4 | 上游已修（验证） | 同上 | dry-run 全过 |

=> 补丁器从"打 2 处 + 验证 4 处"变成**纯验证器（6 处全验证）**。**保留它当回归闸门**：
上游若哪天又改坏形态，`fail-closed` 会拦住，而不是静默编出差版本。
`LLAMA_CPP_COMMIT` 未变（`3cf03257...`）=> llama.cpp 包继续复用，不重下。

**(2) 可能直接改我们读数的三条（升级后必须重测，不能沿用 0.1.40.4 的分母）**

- **#1353「专家已在 RAM 时的 prompt reader 路径」**：当按地读的 GGUF 专家命中 page cache 达 90% 以上时，
  改用**少线程档**而不是 32 线程 SSD 档（官方：某 reporter 的 RAM-resident prompt 曾因此慢 4-7 倍）。
  **我们正是这个场景**（24,576 专家全驻 RAM + GGUF in place），但官方在 4x R9700 上测到"无变化" => **必须自己测**。
  开关：`STRATA_STAGER_SSD=0/1` 强制走哪条 => **这本身就是一个新的单变量候选（P35）**。
- **#1454/#1465 省显存**：prompt 缓冲复用 embedding 存储，32,768 行时省 **320 MiB**（默认答案不变）。
  我们的 VRAM 是紧的（34.03/34.34 GB）=> 省下的 320 MiB **可能变成专家槽或 KV 余量**，要看启动日志的槽位数。
- **tokenizer 缓存**：89K-token 的重复 prompt 编码 **0.32 s -> 0.07 s**（同样 ids）=> 长上下文多轮直接受益。

**(3) 与我们无关或明确不划算的（省得以后再试）**

- 默认变更 (1)：`--batch-groups auto`（多 GPU 层切分）=> 单卡无关。
- 默认变更 (2)：短 prompt 的 CPU 助算（`STRATA_PREFILL_CPU_SHARE`）**官方明写 "Only one NVIDIA GPU without --batch slots;
  layer splits, batch and AMD are as before"** => **AMD 默认不受影响**，我们的 P23 候选仍按 AMD 口径自己测。
- `STRATA_GDN_CHUNKED`（<128 SM 反而慢 0.87x/0.73x）、`STRATA_FS_SLOTS`（0.91-1.00 默认速）、
  `STRATA_ROUTE_RESIDENT`（改答案 KL 0.07）、`STRATA_STAGE_PIN`（**有答案损坏报告，仅测量用**）、
  `STRATA_SM70_TABLE`（V100）、`--peer-device`（多卡）、`STRATA_EMB_REUSE_ACCOUNT`（改 prompt 舍入）。

**(4) 顺带值得记的运维变化**：`strata --version`（以后核版本更方便；0.1.41 镜像实测输出 `strata 0.1.41`）；
引擎挂死自动重启 `STRATA_ENGINE_STALL_S`（90 s 无输出+无 CPU+无 IO+GPU 空闲；需要 psutil，我们镜像里有）；
`--api-key` 支持逗号分隔多键；`STRATA_WATCHDOG_IO_S`。

**(5) CPU 侧（**机主提醒后补测：我们的卡是 AMD，但 CPU 是 Intel**，必须分开判）**

2026-10-08 22:1x 在 166 上**实测**（不从规格推）：

| 项 | 实测值 |
|---|---|
| CPU | **Intel Xeon E5-2696 v4 @ 2.20GHz**，44 逻辑核 |
| AVX2 / FMA / BMI2 | **44 / 44 / 44 个逻辑核都有** |
| **AVX-512（f/vl/bw/vnni）** | **全部 0 个 => 无 AVX-512** |
| 引擎自己的口径（日志实读） | `strata generate: this CPU has no AVX-512: the expert kernels run on AVX-2 (multi-token for the i-quant gate/up rows)` + `CPU pool tasks/phase: 66 (automatic), participating threads: 22` |

=> 我们跑的是 **AVX2 专家内核 + 22 个参与线程**。由此**修正**两处判读：

- **#795「crash on a CPU without AVX-512」由"与我无关"升级为"CPU 侧最该看一眼的风险项"**：
  我们的 CPU **正是那一类**（引擎自己每次都打"no AVX-512"）。官方措辞是 "hardening, not a claimed fix"，
  且新增的构建期检查（反汇编内核 + Intel SDE 跑 CPU 测试，让"AVX2 路径上的宽指令"直接编译失败）
  **对我们这种"从源码自建"的用法是白拿的保障** => 0.1.41 的构建本身就把这条风险压住了。
- **P23（`STRATA_PREFILL_CPU_SHARE`）在 AMD 卡上仍然值得测，而且我们的 CPU 底子够**：
  0.1.41 把它的**默认**只开给"NVIDIA 单卡"，官方明写 "AMD is as before"（= AMD 保持 opt-in，而非"AMD 不支持"）；
  我们 22 个参与线程正是这个旋钮要借的算力 => 候选有效，且**同一家族的 `STRATA_PREFILL_CPU_SHARE_MAX=3072`
  （把受益域从 <1024 扩到 3072 token）也该一起测**（并入 B2 作为次级臂，不单独占一行）。
- 与我们无关的 CPU 类条目：`STRATA_GDN_CHUNKED`（要 128 SM，我们是 GPU 侧 60 CU）、`STRATA_STAGE_PIN`（P100 口径）、
  Q2_0 档（要 AVX-512 快速内核，我们本来就用 UD-IQ4_XS）。

---

## 2 方案（优化后的顺序）

| 档 | 事项 | 判据 / 说明 |
|---|---|---|
| **W1** | **升级到 0.1.41**（建镜像 -> 建容器 -405 -> 切换 -> 复验） | 补丁面 0；切换走 `switch` 脚本（自带 300 s 轮询 + 自动回滚） |
| **W2** | **升级闸门（标准化）**：`升级后必跑` = 服务面四项 + **中性矩阵** | 服务面：`/v1/models` 200 + `/proc` 三项参数 + `verify_config.py` FAIL=0 + LIVE md5 不变；<br>中性矩阵：B1 那套（3 档长度 x 现役参数）约 10 分钟，确认新引擎没动我们的数 |
| **B1b** | **prefill chunk 调小以让短会话吃上复用**（0.1.40.4 上已跑完三臂，**结论成立**，见 §5） | 收口还差**三件**：(1) **答案是否变**（chunk 会改 prompt 路径的累加顺序 => 必须做低比特差异检查，不能用"看起来一样"代替）；(2) 在 **0.1.41 上复核**（引擎换了账要重开，且 #1353 可能改 prompt reader 路径）；(3) 把**冷预填代价**写进结论（实测 -11%）。三项齐了才谈采纳（动的是**基线 P10** + P34 的值） |
| ~~B7~~ | ~~**`STRATA_STAGER_SSD`（新候选 P35）**~~ **已完成：无差 => REJECTED**：强制 prompt reader 走/不走 SSD 档 | #1353 的目标场景正是我们；机制判据看日志里的路径/线程档，吞吐辅助（预填分辨力 1.2-1.7%） |
| **B3** | 多轮复用（`--conversation-cache-mib` / `pin=N`，P31/P33） | 0.1.41 修了**满缓存时的淘汰逻辑**（#1347）=> 该功能值得在这版上重测 |
| **B2** | `STRATA_PREFILL_CPU_SHARE=auto`（短 prompt TTFT） | AMD 口径自测；官方警告**答案非逐位一致**（KL 0.004-0.025），必须同时报 |
| **B6** | `STRATA_MMVQ_IL` 命中判定（P30） | 读源码判定即得结论，无需发车 |
| **B4** | `STRATA_SPEC_GUMBEL=1`（P29） | 必须采样口径（temperature>0），>=5 轮/臂 |
| **B5** | `STRATA_GR_SPLIT=1`（P28） | 预期 ~3%，低于分辨力 => 只用机制判据 |
| **C4** | `gen_config.py` / `verify_config.py` 的 `_sshutil` 自包含缺口 | 工具件，不走参数通道 |
| **C5** | `docker logs` 拿不到终态启动行 -> 回写 `W709_HANDOVER.md` §4 避坑 | 运行期避坑 |
| ~~C1~~ | ~~独立对抗性审计重跑~~ **已完成（两轮）**：22:2x（`W713_AUDIT.md`）+ 23:0x（`W713_AUDIT2.md`） | 见报告两件 |
| **C3** | 旧镜像/容器清理（0.1.39 / 0.1.40.1 / 0.1.40.2 / 0.1.40.4） | 走 `docker-disk-truth` 技能；每次升级多留一个镜像，该定保留策略了 |

**顺序**：W1 -> W2 -> B1b(复核) -> B3 -> B2 -> B6 -> B4 -> B5 -> C4/C5 -> C3。

---

## 3 「升级闸门」标准化（本方案的实质优化）

上游一周发约 20 个 release，我们已连升 4 次（0.1.40.1 -> .2 -> .4 -> .41）。
每次都靠人工重编"中性验证"，既费神又不可比。**固化成一条脚本**，内容与判据如下：

```
deploy/scripts/_upgrade_gate.sh <新容器名>
  第 1 步 服务面（约 1 分钟）
     /v1/models 200 且 n_ctx=262144
     docker exec 读 /proc 的引擎 cmdline => 三项现役参数在（--pcie-frac 0.20 / --spec-min-p 0.70 / --prompt-cache-every 8192）
     本地 verify_config.py => FAIL=0
     LIVE config md5 必须仍是 d2b10f0c4e8293ba010614c7acc70bea（未改参数）
  第 2 步 中性矩阵（约 10 分钟，Z0=off）
     bench_prefix 400（18,084 tok）：冷预填 tok/s + 温 TTFT + reused
     与**上一版同口径读数**比：落在分辨力内 => 记"中性"；超出 => 单独立案追因
  第 3 步 记一行结论进 W7xx_UPGRADE.md（版本 / sha256 / 镜像 ID / 三项读数 / 判定）
```

**为什么要这样**：本次升级 0.1.41 有三条可能改读数的改动（#1353 / #1454 / tokenizer 缓存），
"感觉没变"不算证据；有了闸门，每次升级 **10 分钟买一份可比的证据**，且**跨版本可对齐**。

---

## 4 风险与前置

1. **升级会打断本会话自己的推理**（166:8090 是本会话后端）。实测可控：把"停+起+轮询"放在**同一次工具调用内**，
   实测停机窗口 **35 s**；失败自动回滚（见 `W712_UPGRADE.md` §3.1）。
2. **B1b 已于 22:12 干净收尾**（0.1.41 镜像是在它之后才建的）；本条纪律已满足；日后若并发跑波，仍须等它收尾再建镜像/切换：
   在 166 上编译（44 线程）和重启容器都会污染它的读数。
3. 升级后 **0.1.40.4 的全部读数都要重新标注版本**（本项目铁律：引擎变了账要重开）；
   本方案第 2 档就是为此存在。
4. 旧容器继续保留做回滚：`-401` / `-402` / `strata166` 均 `Exited` 保留（**现役 `-404` 不在此列**：它在下次切换后才会变成旧件）。

---

## 5 附：B1b 结论（已在 0.1.41 上收口，2026-10-08 22:44-23:00，Z0=off）

三臂 x 三档矩阵（0.1.41 / 容器 -405；臂末断言 `/proc` 实际值；档内 2 轮）：

| 档（PARAS 段数） | **A: `auto`/8192（现役）** | **B: `4096`/4096** | **C: `2048`/2048** |
|---|---|---|---|
| 25（~1,210 tok） | 4.57 -> 4.607 s，`0` | 4.57 -> 4.570 s，`0` | 4.62 -> 4.581 s，`0` |
| 100（~4,59x tok） | 10.39 -> **10.413 s**，`0` | 12.78 -> **3.059 s**，`reused=4096` | 14.41 -> **2.978 s**，`reused=4096` |
| 530（~23,94x tok） | 49.74 -> **16.846 s**，`16384` | **55.06** -> **9.068 s**，`20480` | **67.83** -> 5.315 s，`22528` |

（与 0.1.40.4 那轮同口径：B-100 12.65 -> 3.593、B-530 55.70 -> 9.240 => 趋势未变，0.1.41 上温 TTFT 略更好。）

**答案是否变（本波新做的判据，原方案漏项）**：同一批固定 prompt、贪心（`temp 0`/`top_k 1`）、每段一次，
每臂把生成文本落盘比 md5：

| 段 | prompt | A（现役） | B（4096） | C（2048） |
|---|---|---|---|---|
| 0 | 1,430 tok | `4b040edc` len 347 | `4b040edc` len 347 | `4b040edc` len 347 |
| 1 | **6,831 tok** | `8b877ab2` **len 336** | `9ffd3df2` **len 338** | `8b877ab2` len 336 |
| 2 | 18,078 tok | `dbd09331` len 355 | `dbd09331` len 355 | `dbd09331` len 355 |

=> **`--prefill` 是会改答案的旋钮**：B（4096）在 6,831-token 段上连长度都变了。C（2048）这三段恰好与现役一致，
**但只有 3 个样本，不构成"安全"的证明**。（与 0.1.41 那条 CPU 助算"改答案末位"同性质。）

**判定（三条一起摆）**：
1. **收益真实**：4.6k 会话温 TTFT **10.41 -> 3.06 s（-70.6%）**；23.9k 温 16.85 -> 9.07 s。对多轮增长式会话是约 2 倍量级（5 轮 4.6k：约 52 s -> 约 25 s）。
2. **代价真实**：**冷预填变差** 23.9k 49.74 -> 55.06 s（-11%）、4.6k 10.39 -> 12.78 s（-23%）；一次性长文档是净亏。
3. **答案会变**（上面实测）=> 作为**基线参数**（P10）改动，等同于让每一条回复都换数值路径，**当前不建议采纳**。
4. 盲区未解：`<4,096` 的极短会话三臂一律 `reused=0`（chunk 机制所限，换任何值都无效）。

**处置**：**不改基线 P10**；本结论已写进 register **P10 的 evidence**（值/状态不动，仍 35 行 / 16-12-7）。
若机主要拿这 70% 的短会话提速，可**单独选时段**临时切（脚本 `switch_strata.sh` 不涉及参数；改 `--prefill` 仍须走 register 通道）。
**更干净的替代路径（建议）**：向上游提 feature request ---- 让可复用 checkpoint 落在**子 chunk 边界**而不改 prefill chunk，这样既不换数值路径、又能补上短会话盲区。

---

## 6 全量账：已做 / 没做 / 重做（基准 2026-10-08 23:0x CST；**2026-10-09 19:4x 再更新**：§6.2 #2 的 P31 与 P33 均已处置、#3 P23、#8 C4、#9 C5 已关；此前 02:2x 已关 #4、已建 §6.3 #1；**20:1x 再更新**：#2 的 P33 已处置、#6 的 P28/P32 已关；**20:2x** 补 #12 vision 核验（此前漏在账外）、#11 补入 W724 的 PR 候选）

> [!] 本节曾因作者一次"截断到标题再续写"的误操作被整节删除（同步替换 §5 时），
> 已按当前真实状态**重建**；重建依据 = 本会话的各次落盘脚本与 `W713_AUDIT.md` / `W713_UPGRADE.md`。

### 6.1 已做（**截至第 49 条**（第 39 条 = W767、第 40 条 = W768、第 41 条 = W769、第 42 条 = W770、第 43 条 = W772、第 44 条 = W773、第 45 条 = W773 审计、第 46 条 = W773 发车 P46、第 47 条 = W774 0.1.42 升级+登记 P55-P60、第 48 条 = W774 发车、第 49 条 = W774 收车出结论）（原写"20 项 + 第 21/22/23 条"，W752 审计 #7 指出标题停在 23 而表内已到 31），带证据；**register 行数/分布以现算为准**：2026-10-11 00:5x = 75 行数据 / ADOPTED 26 / REJECTED 32 / CANDIDATE 11 / REFERENCE 6）

| # | 事项 | 证据 / 指纹 |
|---|---|---|
| 1 | 工作区迁移 + **原件删除** | 逐文件 md5 全等；删前 "源 ⊆ 目标" + 2 个白名单快照；`MAP_OLD_TO_NEW.md` §5/§6 |
| 2 | 引擎 **0.1.40.2 -> 0.1.40.4** 升级 + 切换 + 复验 + 中性 A/B | 冷预填 -0.33%、温 TTFT -1.7%、`reused` 同；`W712_UPGRADE.md` |
| 3 | **引擎 0.1.40.4 -> 0.1.41 升级 + 切换** | 补丁面**归零**（`PATCH_SURFACE_ZERO`）；镜像 `c45268e786e1`；容器 `-405` 35 s 就绪；`W713_UPGRADE.md` |
| 4 | 升级闸门脚本化 + **首跑** | `deploy/scripts/upgrade_gate.sh`；服务面 7 项全过 + 中性矩阵（三档 `reused` 逐格相同、差 <=1.4%）；**含 0.1.41 新增的 lend-coverage 告警计数 = 0，该观察项当场关项** |
| 5 | 参数最优波（W709）三项 ADOPTED | `--pcie-frac 0.20` / `--spec-min-p 0.70` / `--prompt-cache-every 8192` |
| 6 | 机制三条实证 | chunk 边界规律 / `--prompt-cache-tail` 重复 / 8192-16384 盲区（证据等级已在审计后分级） |
| 7 | **A2 解码基准**（0.1.40.4） | 引擎行 45.7 / 43.3 tok/s；探针中位 43.53 |
| 8 | **B1 边界矩阵**（9 格全中，0.1.40.4） | `<8k` 三臂全 0；`8-16k` 只有 8192 有效（5.87 vs 23.07 s）；`>16k` 8192=16384、32768 归零 |
| 9 | **B1b 收口**（0.1.40.4 首轮 + 0.1.41 复核 + **答案测试**） | 收益 -70.6% 温 TTFT / 代价 冷预填 -11~-23% / **答案会变** => **不改基线 P10**（结论已入 register P10 evidence） |
| 10 | **固化审计 + P34 / P10 结论入 register** | register `f82ccdd743ff...`（本机==166）/ **35 行 / 16-12-7**；`gen_config --write` 后生产 config **逐字节未变** |
| 11 | **三路独立对抗性审计**（+ 6 条 P1 全处置） | `W713_AUDIT.md`（含无法验证清单 6 条与三条元结论） |
| 12 | **CPU 侧实测**（Intel / 无 AVX-512 / AVX2 + 22 线程） | 本件 §1 (5)；修正了 #795 与 P23 的判读 |
| 14 | **B7 实测：`STRATA_STAGER_SSD` 三臂无差（<=0.1%）** | 引擎 `/proc` environ 实读确认 env 生效；机制行只在自动分支打印；register **P98 = REJECTED** |
| 13 | 通用切换脚本 | `deploy/scripts/switch_strata.sh`（旧容器自动探测 + 自动回滚），取代"一次升级一个专用脚本" |
| 15 | **W717：P31 采纳 + C4/C5 关项**（2026-10-09 19:1x） | 上游 parity 终审 P31（状态逐字节 PASS）=> register ADOPTED/4096 + config 推 166 + `-407` 重启 + `verify_config.py` **PASS=18**；C4 工具件自包含（并修 `live_cfg` 旧文件名 bug）；C5 避坑回写两条。见 `W717_P31_PARITY.md` |
| 16 | **W718：P23 关项 + 核验器缺口修复**（2026-10-09 19:3x） | P23 `STRATA_PREFILL_CPU_SHARE` 源码级判定（上游宏缺陷致 banner 误开）+ 两臂实测（机制真生效、零收益）=> register **ADOPTED / 0**（显式关）；顺带修 `verify_config.py` 的 **ENV 面缺口**（此前只查容器 `Config.Env`，漏 config `env` 段）=> 复验 **PASS=19 FAIL=0**。见 `W718_P23_CPUSHARE.md` |
| 17 | **W719：P33 契约确认 + 实测**（2026-10-09 19:4x） | `strata_prefix`（pin=N）契约补齐（**请求体顶层**，三种写法；非法值 400）；长文档 4 轮追问两臂**无增量**（该窗口 `evictions=0`；**W735 更正**：现役驱逐计数已到 5，"预算够"非恒真）=> register P33 保持 **CANDIDATE**；**副产品**：同实测在生产参数下复证 P31（轮 1 冷 11,785 ms -> 轮 2-4 826/1,207/946 ms，-93%~-90%）。见 `W719_P33_PREFIX.md` |
| 18 | **W720：P28/P32 关项 + P29 口径勘定**（2026-10-09 19:4x） | 走『读源码即判、零发车』：**P28 `STRATA_GR_SPLIT` -> REJECTED**（~3% < 解码分辨力 9.5-15%，且 'sums in another order' **破坏位一致**，默认关）；**P32 `--kv-grow` -> REJECTED**（上限仅 +93 槽 / +0.95%）；**P29 `GUMBEL` 保持 CANDIDATE**（服务默认口径=贪心 => 默认下空操作）。**并修正 register 的引证行号**（AMD_HIP.md 461->482；fused_gr.cu 1722->1750+1754）。见 `W720_P28_P32.md` |
| 19 | **W727：必备键清单 + 核验器 CFG/SETUP_KEYS 两个新判定面 + `mtp.cpp:428` 实测**（2026-10-09 20:5x） | (1) register 新增**必备键清单 B01-B07**（`SETUP_KEYS` 里我们「不设」的 6 个 + `api_monitor`，逐条写理由）；(2) `verify_config.py` 新增**数据面 (5)**：CFG 面真判（给了值必须逐字一致 / `(不设)` 必须确实不在）**+ SETUP_KEYS 覆盖**（`SETUP_KEYS - (LIVE键 ∪ 声明名)` 必须为空，**SETUP_KEYS 从容器实时取**）=> **PASS=19 -> 24 FAIL=0**，并做 4 个反事实自证「判据非空」；(3) `api_monitor` **据实判不设**（先实测证伪「Monitor 页需要它」：发一个请求后 `/metrics` 的 requests 表自动填充，它来自 `self.history` 与 `api_monitor` 无关）；(4) `mtp.cpp:428` **A/B/A 单变量实测 = 无差**（噪声底 0.94%，A vs B -2.31% / C vs B -1.38%，全在解码分辨力下；中位 B 落在 A 与 C 之间）=> 结论落 register **P35 = REJECTED（保持默认）**，**不提 PR**。见 `W727_SETUPKEYS_MTP.md` |
| 20 | **W728：PCIe 卡片修复（serve 层本地覆写）+ 核验器数据面 (6)**（2026-10-09 21:3x） | 机主报「pcie 还是没数据」。**根因**：上游 `_Amd.read()`（telemetry.py:169-182）**不读 pcie**，只有 `_Nvml.read()`（:97-103）读；而 `Telemetry.sample()` 用 `s.update({f"gpu_{k}": v for k,v in g.items()})` **透传 reader 全部键**（非白名单）=> **修点只有一处**。**改动 21 行**（新增 `_Amd._link_gen()` 解析 `current_link_speed` + `read()` 加三行 `pcie_gen/pcie_gen_max/pcie_width`）；**不读吞吐**（amdgpu 只有 `pcie_bw`，三个整数、语义无文档 => 不采用）。**落地**：`/src` 是容器可写层 => 覆写 + 三件套脚本（`apply`/`revert`/`check_telemetry_pcie.sh`，原始版留档 md5 `e0a011fe...`）；**引擎补丁面仍为 0**，serve 层 +1。**核验**：`_link_gen` 单测 6/6、容器内 `read()` 实测、重启后 `/metrics` 出 `gpu_pcie_gen=4 / gpu_pcie_width=16`、核验器**新增数据面 (6)**（在位 + 生效，两侧 md5 现算）=> **PASS=25 FAIL=0**，并做**反事实自证**（换回原文 => FAIL；复原 => PASS）。register 新增 **X00 `PATCH serve/telemetry.py`**（50 行 / ADOPTED 24）。见 `W728_PCIE_TELEMETRY.md` |

| 21 | **W733：telemetry 覆写审计（机主三问）+ 覆写加固到 v4**（2026-10-09 22:0x） | (1) **前端 `app.js` 已退回上游原文**（md5 与上游逐字节相同 `476da516...`）；后端 `telemetry.py` 仍为本地覆写，本波 **v3 -> v4**（`a6d2d2d8...` -> `7433869abef5...`，+102/-3 行，删的 3 行全是 docstring，`name()` 未动）。(2) **归属更正**：`product_name` 是 **FRU EEPROM 串**（内核文档 `driver-misc` 原文 "as returned from the FRU"，同族 FRU 字段齐备 `product_number 102-D16314-13` / `serial_number 692112000711` / `fru_id 113-AMDD16314130A100-1.02`），**不是此前写的 VBIOS 串**；它写 16GB 而本卡是 **32GB**（`1002:66a1` + lspci 名 + VRAM 31.98 GiB）=> **不改**（硬编码会坑 16GB MI50 / Radeon Pro VII / MI60）。(3) **覆写加固两处**：多卡聚合改**逐卡求和**（v3 会用卡 0 的值覆盖上游合计）+ **只有全链可读才声称瓶颈**（新增 `pcie_path`）。(4) **对别的用户的影响**：**不会崩**（有 fallback；NVIDIA 路径不受影响），但有三处会拿到不准的数 ---- 前两条已修，第三条（`pcie_rx_mb` 在 AMD 是 `(received+sent)*mps` 的**双向合计**，NVML 那边是**纯 RX**，无方向可拆）**无解** => **该覆写只自用、不提上游**；要提须按上游 AGENTS.md 拆成链路/吞吐两件并同时提口径问题。(5) v4 单测 **23/23 PASS**（Linux 假 sysfs 树跑真代码路径 + 反事实 + 多卡聚合三态）；生产 `verify_config.py` **PASS=25 FAIL=0**；register X00 重写（两侧 md5 `36faff7da7149a77591cfd19c5119418`）。详见 `W733_TELEMETRY_AUDIT.md` |

| 22 | **W734：型号 16GB 与 PCIe 波形两处修复**（2026-10-09 22:1x） | 机主报「这两张卡片还是不对」。**(1) 16GB 的出处定案 = 板载 FRU EEPROM**（内核文档 "as returned from the FRU"；本机 `product_number`/`serial_number`/`fru_id`/`manufacturer` 四个 FRU 专有字段齐备；`cat rom` 报 `Invalid argument` 走不通），而实物 **32GB** => **处置 = 一致性规则**（`name()` 把 `NNGB` 与 `mem_info_vram_total` 取整比对，只在不一致时替换；无容量 token 或读不到则不动）=> 真 16GB 卡等其它用户零影响；单测 8/8。**(2) 「PCIe 显示 0.0 却有波形」根因**：上游 `spark()` 的 `top = Math.max(max||0, ...v, 1e-9)` ---- 无上限时按**序列自身最大值**缩放，而 PCIe 空闲真值只有 0.01~0.02 MB/s（50 包 x 256 B）=> 被放大成满幅方波（y 4.00~17.00）；副行是**瞬时值**且 1 位小数故显 0.0。**处置**：轴下限 `1e-9 -> 1`（只降不升）+ 副行 2 位小数、峰值 >= 1 MB/s 时补 `peak`；node 直跑真函数 7/7（反事实 span 13.00 -> 0.26）。**实测**：`gpu_name` = `Radeon Instinct MI50 32GB`、`sp-pcie` y 29.48~29.74、`verify_config.py` PASS=25 FAIL=0（**数据面 6 扩为逐文件**，含反事实报红）。**顺带查实**：前端 JS 真实路径是 `/web/app.js`（`/app.js` 404）。详见 `W733_TELEMETRY_AUDIT.md` §9 |

| 23 | **W735：晚场全面审计（W717~W734，18 波）**（2026-10-09 22:3x-22:5x） | 机主令「对今天晚上的所有对话轮次进行全面审计」。按 `routeb-audit` 四条铁律派 **2 个只读子 agent** 并行审（A=参数与上游线 41 条断言；B=监控与 telemetry 线 38 条），再由我逐条独立复核。**合计 P0=0 / P1=4 / P2=14 / UNVERIFIABLE=11** ---- 结论无一条被推翻：4 条 P1 是(1)W733 把 **v3 的增删数(102/3)** 配了 **v4 的行数(488)**（v4 实为 119/3）(2)register X00 同行自相矛盾（「只动一个文件、app.js 保持上游原文」 vs 末尾「app.js 已覆写」）(3)**508 MB/s 与元组 (4571,4709165,256) 是不同时刻**（元组按公式=1206.7）(4)「全程 evictions=0」被现役 `evictions=5` 推翻（P33 降级理由改为「该窗口无增量」）；14 条 P2 是单位混用（214 MiB 应为 204、93 槽应为 89）、引证行号取不到、归档日期硬编码、账本计数不符等，**全部已改**。**11 条 UNVERIFIABLE 已补证据**：6 个测试/测量脚本 + 9 份输出落 `deploy/tmp/`（含假 sysfs 23/23、`name()` 8/8、spark 7/7、`/proc/12/environ` 实读 `STRATA_PREFILL_CPU_SHARE=0`、同刻吞吐三列逐位吻合、核验器 PASS=25）。另修 `mem_slim.py` 的归档日期硬编码（我自己用正则改坏了 `%` 优先级，已修回并 exec 自证）。详见 `W735_AUDIT.md` |

| 24 | **W739：`STRATA_EXPERT_V2` / `STRATA_TSUM` 的 gfx906 单变量 A/B（R0a/R0b）**（2026-10-10 00:19-00:36） | 8 臂交错（`A B C A2 B2 C2` + `T T2`），臂容器与生产同镜像同 config（臂 config 与生产逐键对比**只差 log+port**，脚本内断言）；读数取引擎自报 `/metrics`（5 请求 / 2000 token / 同 prompt 贪心）。**噪声底 = 0.13%**（A/A2）。**`STRATA_EXPERT_V2=1`：慢 5.60%**（B/B2 = 50,358.2 / 50,375.0，spread 0.03%）**但输出与基线逐请求 5/5 相同** => 位等成立 => register **P36 = REJECTED**（纯性能否决）。**`STRATA_TSUM=1`：-0.32%（噪声内，中性）但使输出失去复现性**（T 偏离基线 0/5、T2 与基线相同 5/5；`V2+TSUM` 同型且该臂 spread 恶化到 2.51%）=> **P37 = REJECTED**（改答案一票否决）。附带结论：上游 `docs/STRIX_HALO.md §4`「gfx1151 默认开 / byte-identical」那族开关**在 gfx906 上必须逐个体检**。生产两次停、均由 `trap restore EXIT` 恢复（末次 00:35:36 / HTTP=200 / config 与引擎 md5 未变 / 核验器 EXIT=0）。

| 25 | **W740：R1 ISA 探针 + R2 IQ4 dot 判决 + R3 MTP 接受长度**（2026-10-10 00:45-01:0x） | 机主令「按候选表做」，并三连问「为何反汇编 / 源在 166 / 我们自己的库」。读**自有库** `KIntegrated/vllm-gfx906-mobydick`（我们 fork，分支 `gfx906-patches-030`），其 `.agents/skills/gfx906-isa-disassembly/SKILL.md` 第一方写明反汇编只答「编译器实际发射 / ISA 可编码 / 二进制与源同否」。**R1**：新 `deploy/tools/isa_probe.py`（bundler + 溯源 + 全量普查；两处实测陷阱：链接后可执行件 `-unbundle` 只吐 1/59、地址 14 位十六进制且助记符在行首）。**R2**：59 个设备 ELF / 1,926,163 条指令里 `v_dot4_i32_i8` 62,596、`v_dot8_i32_i4` **0**、dot2/pk_fma/MFMA 全 0；ISA 探针 4/4（MFMA 如期被拒）=> 走 dp4a+解包，换 dot8 须双方 i4 => **P38 不改**。**R3**：有效接受长度 **1.797**（<2.0）=> **R5 `--mtp-q4` 关闭（P39）**。件 `deploy/W740_ISA_PROBE.md` / `deploy/tmp/_w740_*` · `MEMORY.md` 2897->2849（`Z-19`）。 |

| 26 | **W741：生产容器一轮 bench**（2026-10-10 01:0x） | 一轮、不碰容器、无 A/B。引擎 per-request 自报：**解码 43.4 / 44.9 / 45.2 tok/s**（512-token、短 prompt 全热、贪心、单并发，均值 44.5）；**冷预填 398.7 tok/s**（3060 token / 7.674 s、单 chunk、`reused 0`）；热预填 212-263 ms（76/81 命中）；MTP 草稿接受 0.772（短）/ 0.809（长）；专家缓存 89.6-95.2%。**Z0 未固定（口径已声明）**，测后 `util 0% / 48C / 18 W`（上限 225 W）。输出 3 次 sha16 互不相同 => 复证 W739。`deploy/W741_PROD_BENCH.md`；证据 `deploy/tmp/_w741_bench.json`。 |

| 27 | **W747：生产容器自比（我们跑过的配置里它是不是最快）**（2026-10-10 01:2x-01:3x） | 机主令「自己跟自己比，不是最快就找出最快的并重现」。扫 235 条历史 per-request 读数 （`_w747_scan.tsv`），只比**同引擎 0.1.41 + 同 pack + 同形状**（pt=85/gen=400）；主判据用 **ms/step**（剔净出/草稿轨迹效应）。跑过的 5 个配置排行：**现役默认最快**（生产两轮 45.18 / 46.22 tok/s，ms/step 44.09 / 40.47），`EXPERT_V2` 慢 5.6%，`TSUM` 并列但不可复现，`MTP_SHARED=0` 无差。**重现**：直接打生产 `8090` 两轮共 10 发（不碰容器），逐发引擎自报。**顺带确证**：生产日志里 18 条 pt=85 是 W727 臂写的（共享 log 路径），引用前须剔除。见 `deploy/W747_PROD_SELF_RANK.md`；证据 `deploy/tmp/_w747_scan.tsv` / `_w747_prod_r2.json` / `_w747_prod_log_tail.txt`。 |

| 28 | **W748：59.9 tok/s 能不能再跑出来（复现）**（2026-10-10 01:4x-01:5x） | 机主问「你那个 59 的还能跑出来吗」。查明那两条（生产日志 ln244/254，`pt=6849/gen=32`）**出自 W716 的"150 段"探针** `/data/bench_prefix.py`，prompt = **同一句英文重复 150 次**、`max_tokens=32`、`temp 0`；当日 `drafts 22 of 22` **全中** => 每步净出 3.20，而单步 53.5 ms **并不快**。**复刻**：第一轮 hit 仅 0.774-0.898（生产容器重启后缓存未热）=> 34.9-50.8 tok/s；连发 8 次后 hit 升到 0.963 => **8/8 >= 59.2、收敛 64.2 tok/s**、drafts 22/22 或 23/23。**结论：可复现且是稳态下界；W741 §8 的"不可复现"已更正**。`tok/s = 每步净出 / 每步耗时`：前者由草稿命中（文本可预测性）、后者由专家命中率决定。见 `deploy/W748_REPRO_59.md`；证据 `deploy/tmp/_w748_repro59{,b}.json`。 |

| 29 | **W749：优化方向 / 方案 / 计划（含 routeK 源码级思路）**（2026-10-10 01:5x） | 机主令"下面你的优化方向、方案和计划，以及从 ki 的库而来的源码级思路"。**实读三个源**：Strata 源码树、自有库 `vllm-gfx906-mobydick@gfx906-patches-030`（7401 文件，落盘 5 件）、生产实测。**五类发现**：(1) `--mtp-window` **默认 32768 而我们没设**（`generate.cpp:552`），上游说 8192 对 64K +3.5%（P43）；(2) Strata 的草稿深度是**在线自适应**，但"未测窗口"的外推曲线 `kShape[]` 的注释逐字写着 **RTX 5070 的曲线**（`draft_policy.cpp:9-12`）；(3) routeK 在**同卡**实测 L2=8MB / HBM 下限 804-809 GB/s / 生产 MoE 内核只到 24%（绑定约束是延迟不是带宽）；(4) routeK 的 MTP k=3 甜点**由 FA tile 决定**（`Sq_pad=4` vs `8`），不是接受率；(5) routeK 的**死路清单**（dot 指令救 decode / A8W8 / k=4,k=5 / custom all-reduce 乱码 / KVSPLIT 统一）。**计划 10 条**，首位 = A1 `--mtp-window` 单变量 A/B，次位 = B2 非专家张量精度**只读**核查。见 `deploy/W749_OPT_PLAN.md`。 |

| 30 | **W750：完整方案与计划（合并全部待办）**（2026-10-10 01:5x） | 机主令"结合待办你有没有完整方案和计划"。**四源合并去重**：register CANDIDATE **5 条**（P33/P40/P41/P42/P43）、§6.2 仅剩 1 项（上游，已交）、§6.3 是引用纪律非行动项、W749 的 10 条候选（与 register 大部分重叠）。=> **11 条行动项**，其中 **3 条零发车**。分 P0（W2 只读核查 / W10 常量入账 / W1 `--mtp-window` / W3 `SH_STREAM`）· P1（W5 `--kv` 质量门 / W6 §4 串行 / W7 lookup-chain）· P2（W4 逐桶账 / W8 kShape 标定 / W9 并发）。**结合待办才查出的两处缺口**：(1) **P33 的 CANDIDATE 理由已被 W735 推翻**（原文"全程 evictions=0"；现役实测 evictions 会递增到 5+）=> 须改写为"限该单会话窗口"；(2) **并发面与 P97 冲突**（P97 `--batch/--slots` = REJECTED，但理由是**使用面判断**"单用户不需要"、从未实测，与 P30 那种源码级证死不同类）=> 要做 W9 必须**先把 P97 改成 CANDIDATE**，否则等于绕过账本。另列**组合约束**（同路径不可组合测 / 臂须交错 / 停生产 + trap 兜底 / 只用 0.1.41 同批次）与**不做清单**。见 `deploy/W750_MASTER_PLAN.md`。 |

| 31 | **W751：核对并补全 ---- W749 并入 W750**（2026-10-10 01:5x） | 机主问"W749 的内容有没有合进去了"。**逐项机械核对**（不是靠印象）：W750 只吸收了 W749 的**行动项名称**，**丢了六类**：(1) 源码级引证表（file:line）(2) B1 的关键事实（`kShape[]` 来自 **RTX 5070 曲线**）(3) B3 的关键事实（`full_attn` 占 64k->120k 步时增长的 **87%**）(4) routeK 的**三条测量纪律**（standalone 不迁移 / graph A/B 才是门 / PPL 在混合注意力上不可靠 + `stop_agreement` 抓不到坏分布）(5) MTP 深度是 tile 问题的判据（`Sq_pad=4` vs `8`）(6) KVSPLIT 的 shape-aware 教训。=> **已全部补进 `W750_MASTER_PLAN.md`**（新增 §7.5 源码级引证表、§2 三条纪律、W1/W2/W4/W8 各补源码依据、不做清单补 KVSPLIT 与 fused-gather/fused-topk 两行），11025 -> **14538 B**；并在 `W749_OPT_PLAN.md` 顶部标注"已并入 W750，保留为引证层"。12/15 项（两次清单：`_w751_merge.py` 12 项、`_w751_verify.py` 15 项）复查全 YES；体量 11025 -> 14538 -> 15474 -> **18674 B**（W752 审计修正 8 处见第 32 条；W753 又插入 §0.0 执行版，见第 33 条）。 |

| 32 | **W752：审计 W747~W751（"说的 vs 落盘的"）**（2026-10-10 02:0x-02:1x） | 机主令"感觉你说的不一样。审计吧"。按 `routeb-audit` 四条铁律，**分两层**：**A 层（会话表述 vs 落盘，只有当前会话能审）** + **B 层（落盘件彼此之间，派 Explore 子 agent 独立审）**。合并 = **A 层 5 处（3xP1）+ B 层 13 处（5xP1 / 8xP2）**，去重后**修正 13 处**：(1) W750 §0 三处的 `CANDIDATE 5` -> **6**、`REJECTED 28/CANDIDATE 5` -> `27/6`；(2) W750 §1 W9 行的 `P97 = REJECTED` -> **CANDIDATE**（§4/§5 早已改，漏了这一处）；(3) **W748 §3 的归因不等式为假**（原文"hit 0.963 > 96.8%"，实际 0.963 < 0.968）=> 真因是**草稿每步净出**（`23/23` 的 net 3.56 对 `22/22` 的 3.20）；(4) W750 §5 补 **3 行 routeK 死路**（`--disable-custom-all-reduce` / SYV-12 / QSA+GGUF）；(5) 日志里 `pt=85 = 23 = 18 + 5` 是**只跑完第一轮**的中间值 -> **28 = 18 + 10**；(6) W750 §2 补 **W11 阶段**（原 11 条行动项只编到 10）；(7) 账本 §6.1 标题停在"21/22/23" -> **截至第 31 条**；(8) W750 §0 的"W749 候选 10 条" -> **12 项（A/B/C）/10 行计划**（两套编号）；(9) W750 §4 缺口 1 改为"已改"；(10) W741 头部时点标注"起于 01:0x、后被追加到 01:5x"；[?] 账本 §6.2 #11 的"三件（2PR+1FR）" -> **已交 3 PR + 2 issue + 4 评论**；[?] W749 里 routeK 原文体量**补标 chars**（5/5 与 chars 完全一致，非数字错）；[?] 第 31 条的"12 项" -> **12/15 项（两次清单）**。**根因**：改一个对象的裁定后**没有按对象 ID 全文 grep 逐处同步**（P97 同时残留在 W750 §0 与 §1；P33 同样）---- 与 `W735_AUDIT` 的 P1#2 同族。见 `deploy/W752_AUDIT.md`。 |

| 33 | **W753：在 W750 顶部插入「现时点执行版」**（2026-10-10 02:1x） | 机主令"**现阶段的完整方案和计划**"。W750 此前经历"首版 -> W751 补全 -> W752 审计修 13 处"，结构与口径已正确但**有补丁痕迹**（§2 插了 P3 段、§5 补了 3 行、§0 改了三处）。=> 在 §0 之前插入 **§0.0 现时点执行版**，把这四样放到最前：**现状快照**（register `25/27/6`、生产 `-407` + 补丁面 0/serve 覆写 2、上游 3 PR + 2 issue + 4 评论等回音、已收敛结论、三处空白）、**P0 立即行动序**（W2 只读核查 -> W10 常量入账 -> W1 `--mtp-window` -> W3 `SH_STREAM`，其中 2 项零发车）、**发车前必做三件**（逐键对比 / 停生产 + trap 兜底 / 三协变量）、**P1/P2/P3 与前置**、**引用口径**。体量 15474 -> **18674 B**；W750 仍是唯一权威计划件。 |

| 34 | **W754：W2 非专家张量精度核查（P0 第 1 项）**（2026-10-10 02:1x） | 机主令"按计划推动"。**列义先取自源码**（`src/core/weights.cpp:136` 注释 + `:168-173` 的 19 字段 sscanf），再统 `index.txt` 的 1079 张量。**结果**：`kind=0 / bits=8 / group=32`（**Q8_0**）**303 个**且 dst=0（native 服务）---- 其中含 **`output.weight`（lm_head）· attn_qkv · attn_gate · ffn_{gate,up,down}_shexp**；`kind=4`（**BF16**）**483 个 / 1407.11 MiB**；F32 292 个 / 9.60 MiB；F16InF32 1 个。**判定**：**routeK 的 T1（把未量化的 lm_head/qkv/shexp 做 int8）在 Strata 上直接前提不成立**（那些已 Q8_0，8->8 无 byte-side 收益）；**但查出更聚焦的新目标** ---- `hc_*` 四类（`hc_attn_up/down`、`hc_ffn_up/down`，4 x 48 层 x 6.25 MiB = **1200 MiB = BF16 的 85.3%**）+ `ffn_gate_inp`（120 MiB）合计 **1320 MiB = 93.8%**，每层都有、每步都参与。**收益路径与 routeK 不同**（我们的是 dense 常驻，routeK 赚的是 HBM 地板）=> **下一步是 ISA/roofline 前置探查（B3 逐桶账 + 反汇编），不是直接发车**。见 `deploy/W754_W2_NONEXPERT_QUANT.md`；证据 `deploy/tmp/_w754_index.txt`。 |

| 35 | **W756：上游社区 bench 的规范核查 + 我们的报告方案**（2026-10-10 02:2x） | 机主问"上游有没有 bench 的标准，我们可以基于我们的硬件报一个"。**有正式规范**：`docs/COMMUNITY_BENCHMARKS.md`（178 行）---- 含 **What to record**（硬件/软件/模型/设置/负载五组）、**How to measure**（**每格 >=3 次**、给中位数与范围、区分"新处理 vs 复用"并报引擎的 reused/read、**禁止用"生成数/总请求时"当 decode**）、**可选的正确性检查**（官方 `tools/needle_bench.py`，5858 B）、**提交流程**（fork -> `bench/results/YYYY-MM-DD-community-<标签>/` -> PR 到 `main`，结果 PR 与引擎改动分开）与**报告模板**。**已有 5 份社区报告**，其中 gfx906 那份是 **2x MI50 16 GB + `layer_split 27`**（JeanP00l，0.1.38+4 PR）。**关键缺口**：`docs/AMD_HIP.md:504-506` 逐字写着 *"Not done: ... **a single-card run** ..."* => **上游自认 gfx906 的单卡 run 未做**。**我们的机器正好是那个形态**（1x MI50 32 GB），且与已有报告在四处不同：单卡 vs 双卡、**UD-IQ4_XS（4-bit）vs Coder IQ1_M（1-bit）**、**262144 vs 131072** 上下文、`--kv k8v4` vs `--kv int8`。**方案**：按模板出 `bench/results/2026-10-10-community-mi50-32gb/`，速度 = 3 长度（4096/32768/128000）x 3 runs，needle = 32k/128k/262k x 深度 10/50/90；**都直接打生产 8090（HTTP），不需要停生产/不需要臂**。见 `deploy/W756_UPSTREAM_BENCH_PLAN.md`。 |

| 36 | **W760：W1（`--mtp-window`）/ W3（`STRATA_SH_STREAM`）单变量 A/B + 参数固化**（2026-10-10 02:1x-02:5x） | 机主令"按计划推动"，随后澄清"我是说跑的结果，参数的固化"。**6 臂交错**（`A B C A2 B2 C2`），**64K 上下文**（`prompt_tokens=64064`，每臂 1 冷 + 4 温，`gen=64`，贪心）；臂 config 断言 `BASE_DIFF [log,port]` / `WIN_DIFF [args,log,port]`；现场确认 **臂 B 的 args 尾部含 `--mtp-window 8192`**、**生产 config `has mtp-window: False`**。02:16 发车、**02:36:52 收车**、生产 02:37:33 恢复。**结果（decode 中位）**：基线 A **44.12 tok/s**（臂内差 0.30%）· **B `--mtp-window 8192` = 45.61 => +3.39%** · C `SH_STREAM=1` = 44.06 => **-0.13%（无差）**。**B 的机制自洽**：它的 `ms/step` 反而更慢（74.28 对 72.54），收益全在**草稿接受率**（223/239、228/242 对 220/236）=> 每步净出更高（与 W748 的分解式一致），且与上游 `STRIX_HALO.md:126` 的 **+3.5%** 吻合。**答案核验**：COLD（首次、`reused=0`）六臂 sha16 **全同**；WARM 期分歧里**基准组 A 自己也在震荡**（WARM1 `603998b4` -> WARM3 `66f879c7`）=> 属 W739 已知的会话态效应，**不构成"改答案"**。**回写（按铁律通道）**：**P43 CANDIDATE -> ADOPTED（值 8192）**、**P40 CANDIDATE -> REJECTED**；`gen_config.py --write` 生成新 config（args 尾部出现 `--mtp-window 8192`，ADOPTED 25 -> **26** 行）-> 推 166（cfg `6261ddf8a81b...` / reg `576ee06687bd...` 两侧一致）-> **重启生产**（45 s 就绪、HTTP 200）-> **`verify_config.py` PASS=26 FAIL=0**（P43 行由 SKIP 变为 **PASS**）。见 `deploy/W760_W1_W3_AB.md`；证据 `deploy/tmp/_w760_arms_raw.txt` / `_w755_ab.out`。 |

| 37 | **W763：参数固化倒查（10-09 晚 ~ 10-10 02:45）**（2026-10-10 02:4x） | 机主问"从昨天晚上到现在有没有遗漏了，该固化的参数是不是都固化了"。**机械倒查**：两日志 **43 波**、出现过的参数名（CLI 46 + ENV 22）逐个查 register。**查出 17 个真参数从未入账**：`STRATA_{IO_PREFETCH,FILL_AHEAD,FS_AHEAD,FETCH_THREADS}`（**io-prefetch 族**，正对本机"专家流式读"的瓶颈）、七个 drafter/spec CLI（`--coupled-draft` / `--lookup-chain-min` / `--mtp-draft-vocab` / `--no-spec-split` / `--spec-follow` / `--spec-split` / `--window-hashes`）、以及 `STRATA_EXPERT_V2K` / `EMB_REUSE_ACCOUNT` / `PF_SWITCH_MIN_T` / `KV_GROW_HOLD` / **`GFX1151_DEFAULTS`**（P41 那族的总开关）/ `--pcie-mode`。**回源码核实 17/18 命中**（`generate.cpp` 等 + 11 个还在 `docs/DETAILS.md` 等登记过）=> 不是幻觉、是账漏了。**已补登记为 P46/P47/P48（全 CANDIDATE）**，register 60 -> **63 行**（ADOPTED 26 / REJECTED 29 / CANDIDATE 7 / REFERENCE 1）；另排除 Chrome/rocm-smi/gen_config 的 flag 12 个、别的项目 1 个（`STRATA_PREFILL_LAYER_MAJOR` 是 routeK 的）、环境必需 1 个。**逐段核对**：43 波里产生参数级结论的 **12 波全部有着落**。**局限**：倒查面是"日志里提到过的"，引擎里有而日志没提的**不在覆盖面内**；更严的一步是**「引擎 `--help` 全量 vs register 全量」的差集**（已记入待办）。见 `deploy/W763_INVENTORY_AUDIT.md`。 |

| 38 | **W765：参数落地审计（26 行 ADOPTED 是否真落容器）+ 4 条修正**（2026-10-10 02:5x） | 机主令"审计。还有是否全部落生产容器了，固化的有效参数"。按 `routeb-audit` 派只读子 agent 独立审 （`P0=0 / P1=0 / P2=4 / UNVERIFIABLE=6`），我逐条复核。**正面结论**：**P43 三面全中** ---- config args 含 `--mtp-window 8192` · **引擎进程 cmdline（`/proc/12`）末端就是 `--mtp-window 8192`** · 引擎 environ 含 P11/P23；源码侧 `generate.cpp:1801 -> o.mtp_window`、`mtp.cpp:331/358/819/1143` **确有使用**；md5 三处一致（本机=166宿主=容器内）；时序 config mtime 02:41:52 -> 容器 StartedAt 02:41:59；**26 行 ADOPTED 逐项有落点**（17 CLI + 2 ENV + 4 CFG + 1 PATCH + 2 TOOL）；**反向干净**（无"容器有、账上没有"）。**4 条 P2 全部成立、全部已修**：(1) `verify_config.py` docstring 的"真的生效"强于其判定面（不读 /proc）=> 已补"判据面的边界"段；(2) `W764` 报告的三面漏了**引擎 environ 面** => 已补；(3) **B00 证据栏还写着 `MI50 16GB`**（W734 修 `name()` 后没同步）=> 改 32GB（X00 里 4 个 16GB 经查是叙事、不改）；(4) **备份链断在 00:39** ---- `P43/P40` 在 27 份备份里 **0 命中** => **我自 W739 起 7 个波次裸改 register、违反 `MEMORY §1`「改既有长件前先备份」** => **子 agent 判 P2，我升为 P1**，本轮已恢复备份（register x3 + verify_config x3，链 30 份）。见 `deploy/W765_PARAM_AUDIT_VERDICT.md` 与 `deploy/W764_PARAM_LANDING_AUDIT.md`。 |
| 39 | **W767：`--kv` 四档质量门（P1 首项）= 用上游原生 teacher-forced 探针建门 + 出读数**（2026-10-10 20:0x-20:5x） | 机主令「继续」（承 W766 交接：W5 是 P1 第一项、唯一带正确性风险、前置 = 先建 KLD harness）。按铁律先加载技能 `routek-kv-precision-ab`。**门的来源不是自建**：`generate.cpp:9543` 的 **`STRATA_LOGPOS=<file>` + `STRATA_LOGPOS_TOPK=K`**（实现 `verify.cpp:2202 Verifier::window_logprobs()`），每行 8 列定值 + K 个 `id:logprob`，其中 **`is_top` 列本身就是 greedy 一致率**、`extra` 列（248046 = `<|im_end|>`）给出 stop 概率；上游已用它发过两份社区报告（`bench/results/2026-10-03-v100-prompt-attn` 为配方源头 / `2026-10-04-rdna2-fp16-prompt`），方法论文档 `docs/UNSLOTH_Q4.md`。**否掉两条**：`--dump-logits` 在 native pack **不可达**（`generate.cpp:11815` 逐字 "A native pack never runs the per-token loop `--dump-logits` reads"，其诊断件 `tools/logits_identical.py` 不在 0.1.41 树内）；上游 `quality.py` 的两个数据集不在树内。**关键语义**：`generate.cpp:9397` `if (no_short or b - a > req_short_read) return false;` => **只有 fresh <= `--short-read` 时整段才被评分** => 必须**两次请求**（先灌前缀、再发尾段）；首车我按"末尾 640 个 token"设计 => 每臂只落 4 行（实测暴露）。**结果**：5 臂（`f16a`/`f16b`=fp16 x2 作 self 控制 / `k84`=k8v4 / `i8`=int8 / `q40`=q4_0）各 **1394 个配对位置**；**self 对照 KL 恰好 0 / argmax 100% / top10 100% / PPL 逐位同 => 读数下限为零**（routeK/vLLM 的 self 是 2.97e-3，噪声底把信号吞掉）。KL 中位 int8 0.0416 < **k8v4 0.0704** < q4_0 0.1050（与 V 量化强度严格同序，剂量-响应成立 -- **该归因已作废，见 W767 §8 / W768 / W769：驻留布局与主效应同量级**）；生产值 k8v4 相对 fp16 在 **18.1% 的位置上 argmax 不同**，KL 高于上游"只改舍入顺序"对照（0.023-0.090 / argmax 91-98%）**6-13 倍** => **差异在舍入带之外**。**换五个估计器交叉核对**（`kl_prop` / `kl_inter` 零填充 / `tv_union` / `jsd` / `d logprob(top-1)`）**排序一致**，但零填充版只有一半 => **绝对量级依赖口径**。**方向不可判**：PPL 反降（42.59 -> 35.51）、自身 top1 命中反升、自身 top-1 logprob 反降、停止质量反降 => 四个标量互相矛盾。**结论：分布实质不同、方向未判、不改任何参数**；未做任务级门与驻留对照。落 `deploy/W767_KV_QUALITY_GATE.md`（**20,801 B（W773 实测）**，含 W768 的 §8/§9 追加；W767 成文时 11,949 B -- W773 审计 #4 更正）；register **P04 证据/裁定已补**、P42 标"W767 已做"、**新登记 P50（REFERENCE）**，两侧 md5 `5404b9e188d2...`，核验器 **PASS=26 FAIL=0**。 |
| 40 | **W768：`--kv` 质量门的驻留对照 ---- 归因被否定**（2026-10-10 21:0x-21:2x） | 承 W767 §4 的未排除项（各臂 `--expert-cache auto` 随 KV 占量不同；引擎对命中/未命中的专家走不同代码路径）。设计成**正面反例**：**固定 `--kv`**、只改 `--expert-cache`。3 臂 （`rc6` k8v4@6000 / `rc9` k8v4@9000 / `rf6` fp16@6000），同语料同 **808 个位置**（tier1+tier2），每臂起车前从备份恢复**同一份 profile**（md5 `ff1bc654...`）。**实测驻留** rc6 8632 / rc9 9856 / rf6 8143。**结果**：`f16a`-vs-`f16b`（驻留相同）**恰为 0**；**`rc9`-vs-`rc6`（`--kv` 完全不变、仅驻留 +1224）= KL mean 0.366 / med 0.031 / argmax 87.4%**；`rf6`-vs-`rc6` = 0.516 / 0.069 / 83.4%；主车 `k84`-vs-`f16a` = 0.404 / 0.076 / 83.5%。**主车差值落在"驻留对照 0.366"与"KV 对照 0.516"之间 => 归因不成立，W767 §3 第 2 条结论作废**（报告加 §8，不改历史记录）。**仍然成立**：门的 self=0（探针逐位确定）；量级对照（KV / 驻留 / 上游舍入顺序 0.023-0.090）=> **分布差异在本卡不是质量判据**（与 W767 §2.6 标量互矛盾同源）。**下一步**：fp16 臂降 `--max-context` 到 101376（= 262144 x 816/2112）使其 KV 占量与 `k8v4@262144` 相等、两臂都 `--expert-cache auto` => **实测驻留数相同**，此时才是干净的 `--kv` 效应；再加任务级门（needle / 配对 McNemar）。另：本波在落盘时查出**两处压缩器缺陷**（`protect` 行号基准错、L3 去括号会删掉写在括号里的关键结论），已修 + 控制测试，详见报告 §9。 |
| 41 | **W769：驻留匹配的 `--kv` 对照 ---- 分布门被驻留布局主导**（2026-10-10 21:34-21:49） | 承 W768 的"下一步"（把 fp16 的 `--max-context` 压到使 KV 占量与 `k8v4@262144` 相等）。**可控点有源码依据**：`plan.hpp:144` `cache_bytes = pool - kv_bytes - fixed`、`:134` `kv_bytes = kv_bytes_per_token(g) * max_context` => 专家槽位由 KV 占量直接决定。4 臂：`k262`（k8v4/262144，基准）+ `p131`/`p122`/`p114`（fp16 @ 131072/122880/114688），全部 `--expert-cache auto`，同语料同 **808 个位置**（tier1+tier2）。**自校验通过**：`k262` 实测槽位 **9761 == W767 的 `k84`** => 槽位跨车精确可复现（顺带解掉 W768 的疑惑：显式 `--expert-cache N` 不等于最终槽数，`auto` 下才一致）。**实测槽位** 9761 / 9598 / 9696 / 9794，三个 fp16 点**精确共线**（斜率 -0.011963 slots/token），三点独立外推 `slots == 9761` 一致到 1 token 内 => **`MC* = 117446`**（本车未做出零槽差对照：最接近的 `p114` 仍差 +33 槽）。**决定性发现（B 组 = 同 dtype、fp16 无损、评分位置相同、只差 cache 组成）**：`f16a`-vs-`rf6`（**同 dtype 同 MC**，96 槽）= **0.2837** / argmax 91.46%、`p131`-vs-`p122`（98 槽）0.2873、`p122`-vs-`p114`（98 槽）0.3045、`p131`-vs-`p114`（196 槽）0.2864、`rc9`-vs-`rc6`（1224 槽）0.3655 => **槽差为 0 时 KL 恰好 0；一旦不为 0 即跳到 0.28-0.37 的平台，且几乎不随槽数增长（阶跃，非线性）**。**`--kv` 净增量 `>= 0.1434`**（`p114` 的 0.4277 减掉 `<=0.2837` 的伪影；独立路线 `k84`-vs-`f16a` 0.4841 - 0.3655 = 0.119；三条估计一致 0.12-0.14）=> **真实但次级**。**机理**：引擎对 cache 命中/未命中的专家走不同代码路径（`R4 hit path ON` / `token graph hit path`）=> 扰动由"翻转的 token 数"决定，而非"槽差多少"。**结论：分布门在本卡上被"专家驻留布局"主导、原理上无法单独裁决 `--kv`**（因为 `--kv` 的定义就是改 KV 占量，而 KV 占量必然改 cache 组成，驻留伪影不可消除）；**下一步只剩任务级门**（needle / 配对 McNemar）。**新立方法学判据**：凡用分布类指标做 A/B，必须先做一组"同 dtype、同精度、只差非目标旋钮"的对照 ---- 本车正是靠这组才发现门被驻留主导。报告 `deploy/W769_RESIDENCY_MATCHED_KV.md`（含 §7 机理 / §8 局限 / §9 自伤）。 |
| 42 | **W770：上游社区 bench（speed + needle）---- 单卡 32 GB gfx906，兼答 `--kv` 的质量问题**（2026-10-10 22:01-23:04） | 承 W756 的方案（上游 `docs/COMMUNITY_BENCHMARKS.md` 规范 + `AMD_HIP.md:504` 自认 gfx906 的"单卡 run"未做，而已有那份 gfx906 报告是双卡 16 GB + layer split）与 W769 的结论（分布门无法裁决 `--kv` => 只剩任务级门）。**两臂**（`--kv` 是启动参数，不可能同引擎 A/B）：`k84b`（**k8v4@262144，与生产逐位同**，`args_changed=[]`）与 `f16b2`（fp16@262144，只动 `--kv` 值，`args_changed=[21]`）。**数全部取引擎自报**：speed 脚本在发请求前后各记一次日志行数、切出该请求的 `strata serve: prompt <N> tokens = <R> reused + <K> read in <ms> ms (...), <G> generated in <ms> ms (...), drafts accepted <A> of <B>, <C> checkpoints` 行与 `decode expert cache hit rate` 行；**绝不用"生成数/总时延"反推 decode**（规范明令禁止）。**speed**：15 run 全成功、**全部 `reused 0`**（prompt 头部放不同 nonce => 首 token 即不同）；`k84b` 4096/32768/128000 x3，`f16b2` 32768/128000 x3。**实际 prompt token 少于目标**（脚本按 2.4 chars/token 估，本机实测 3.0-3.3）=> 3141 / 26038-26040 / 93337-93339，**照实报实际值**（规范要求 Actual prompt tokens 独立成列）。**k84b 中位**：prompt 393.80 [361.70..394.30] / 460.70 [457.30..461.50] / 458.80 [458.80..460.70] tok/s；decode 44.70 [38.30..45.40] / 40.70 [38.40..47.50] / 40.70 [35.40..46.80] tok/s；命中率 89.9% / 90.8% / 92.6%。**`--kv` 对照**：prefill 两臂相同（<1%）；**decode k8v4 快 7.7%~16.6%**（40.70 vs 34.90 @26040；40.70 vs 37.80 @93340）、**命中率高 3.4~7.7 个百分点**（90.8% vs 83.1% @32768）=> **省下的 3.8 GiB KV 换来 1714 个额外驻留专家（9761 vs 8047 槽）= k8v4 的机制性收益**。**needle**（官方脚本，容器内跑）：两臂各 **6/6 FOUND**，**paired 6 对、不一致 0**=> **`k8v4` 在该门分辨力内无质量损失**（这是 W769 指向的任务级门的答案）；`262k` 由脚本自身按上下文检查跳过（`skipped (the server's context is 262144)`），记为 skipped 非失败。**产出**：`bench/results/2026-10-10-community-mi50-32gb/`（README 按上游模板 + `speed.json`/`needles.json`/`BUILD.json`/`speed.py`/`engine-timing-lines.txt`），按规范提 results-only PR。本机副本 `deploy/tmp/bench_report/2026-10-10-community-mi50-32gb/`。**自伤**：装配脚本对 `corr` 段漏做 `%` 格式化 => needle 表渲染成 `%s`、`98%%` 未转义；已修并加自检（README 内 `%s`/`%%` 必须为 0）。**已提 PR #1855**（`open` / `mergeable=True` / `+847-0` / 6 文件全为新增，results-only；用用户级记忆的「本机 GitHub API 凭据通道」配方自动开，幂等）。 |
| 43 | **W772：待办盘查 + 三处账实不符修正**（2026-10-10 23:1x-23:2x） | 机主问「后面还有待办吗」。**机械对照**（不靠印象）：`W750 §1` 的 11 条行动项 ---- **已做 5**（W1 `--mtp-window`/W760 · W2 非专家张量/W754 · W3 `SH_STREAM`/W760 · W5 `--kv` 质量门/W767-770 · W10 常量入账/W755）、**未做 5**（W4 逐桶账 · W6 §4 族 · W7 `--lookup-chain` · W8 `kShape` 标定 · W9 并发面）、**等回音 1**（W11 上游）；register 的 **CANDIDATE 7** 全部未测。**顺手修三处账实不符**（同族根因 = 改了"动作现场"、没按 ID 回扫全文）：(1) **`P50`** verdict 开头仍写"（W767/W768/W769 **三车**）"、而**其末尾已含 W770 内容** => 自相矛盾，改"四车"并把 name 补 `-W770`（两侧 md5 `5e15aa4200e0`、核验器 **PASS=26 FAIL=0**）；(2) **`MEMORY.md §4`** 把 **`P33` 错列在"已关"**（register 实为 **CANDIDATE**）=> 移入 CANDIDATE 行、未做清单补全为 7 个编号、"已交上游"补 **PR #1855**（走技能，归档 `Z-40`，2896 字符）；(3) **`W750 §0.0`**（自称"现时点执行版"）已过期（CANDIDATE 6、W5 未做）=> 刷新为 W772 版（18,674 -> 18,477 B；11 个 `##` 标题不变 => 结构完整）。 |
| 44 | **W773：参数固化完整性倒查（该固化而没固化的）+ 补登记 P51/P52/P53**（2026-10-10 23:2x-23:4x） | 机主令「按项目已有流程严格执行、出结果要及时固化以免白跑」。**判据机械化**（不靠印象、且判据自身先过正控）：「真引擎参数」= 引擎 `--help` 全量 ∪ 源码里的 flag 字面；「已登记」= register 的 **name 列**能命中（复合写法 `STRATA_{A,B,C}` / `A / B` **先展开**）。**三次判据自纠**：(1) 首版用 `head -400` 抓的 help 当权威源 => `--mtp-window` 等被误判成"非引擎参数"，**正控失败** => 重抓完整 help（39,074 B / 451 行，落盘 `deploy/tmp/_w773_help_full.txt`）；(2) `--kv` 两字符被正则 `{2,}` 漏掉，正控 9/10 => 改 `{1,}`；(3) P46 的 name 是复合写法 => 4 个 ENV 被误判"无独立行" => 加展开。**最终正控 10/10 PASS**（fail-closed）。**真缺口 7 条**（全按源码复核过）：`--short-read`（**24 次**，门的前提）、`STRATA_LOGPOS`（**19 次**）、`STRATA_LOGPOS_TOPK`（9 次）、`--dump-logits`（W767 判死）、`--layer-split`、`--mtp-max-t`、`STRATA_USE_HIP`。**补登记三行**：**P51**（门仪器族 = LOGPOS/TOPK/--short-read，REFERENCE，含两请求协议与 self=0）、**P52**（`--dump-logits`/`--logits-stride`，REJECTED，`generate.cpp:11815` native pack 不可达）、**P53**（`--layer-split`/`--mtp-max-t`/`STRATA_USE_HIP`，REFERENCE；**`STRATA_USE_HIP` 复核为 67 处 `#if defined(...)` 的编译期宏、非运行期 ENV**）。register 65 -> **68 数据行**（ADOPTED 26 / REJECTED 30 / CANDIDATE 7 / REFERENCE 5），两侧 md5 `cb987cd12ee4`，核验器 **PASS=26 FAIL=0**。 |
| 45 | **W773 审计：今晚 6 车（W767~W772）+ 未审的 W754/W756 ---- P0=0 / P1=2 / P2=11**（2026-10-10 23:2x-23:5x） | 机主令「针对今晚以及之前未审计轮次对话做全面审计」。**双层**：独立只读子 agent（对抗立场，范围 = 今晚六车 + W747~W763 未被 W752/W764/W765 覆盖的 W754/W756）在跑；我方并行核最要紧的两条 P1。**独立复算结论：读数逐位吻合**（子 agent 用与 `_w767_kld2.py` 逐字相同的 `kl()` 口径重写分析器）---- self `f16b vs f16a` KL 0.00000/argmax 100%（n=1394）· `i8` 0.04164 / `k84` 0.07044 / `q40` 0.10497 与 W767 §2.2 表一致 · W768 `rc9 vs rc6` 0.36554、`rf6 vs rc6` 0.51594 · W769 `p114 vs k262` 0.42770、槽位 9761/9598/9696/9794 · W770 speed 15 条引擎行全 `0 reused`、needle 两臂各 6/6 paired 0 不一致 · W754 的 303/483/1407.11 MiB/1200=85.3%/1320=93.8% · W756 规范四条（3 runs/禁除法/needle_bench 5858 B/AMD_HIP:504）**全部逐条命中**。**P1#1（真错，已修）**：`W769 §5` 把 `k84 vs f16a` 记 `0.48406`，而 `W767 §8` 同标签记 `0.40416` ---- **同一对、同一文字标签用了相反参考方向且未声明**。我方独立重算（`_w773_klcheck.py`，808 位置）：`KL(f16a\|\|k84)`=**0.404158**、`KL(k84\|\|f16a)`=**0.484061**。根因 = `_w769_kld2.py:145` 的 `cmp(k84, f16a)` **参数顺序写反**（`_w768_kld.py:95` 写的是 `cmp(f16a, k84)`）。**后果与更正**：W769 的"独立核对 0.48406-0.36554=0.119"应改为 **0.40416-0.36554=0.039**，故"三条估计一致 0.12-0.14"**不成立**（同车 0.1434/0.1319 与跨车 0.039 相差 3.7 倍）---- 这**加强**而非削弱 W769 的主结论（两种"减伪影"的减法给出不同答案 => 该门量不出 `--kv`）。**P1#2（真错，已修）**：`W750 §0.0` 自称"现时点执行版"却仍写 65 数据行 / REJECTED 29 / REFERENCE 3 ---- W773 加 P51/P52/P53 后现态 **68 行 / 26/30/7/5**，drift 系由 W773 自身引入、未回写。**P2 11 条**（W750 §0/§8 计数三口径矛盾 · 账本 item39 体量 11,949 实测 20,801 · W756 写"无 vision"实测 P99 ADOPTED · 槽位 9757/9758 vs 实测 9761 · W767/W769 把"行数"与"唯一位置"混称 · `9751` 笔误 · bench README Method 称"three runs each" 而 fp16 臂只做两长度 · needles.json 的 skip 只记 null · W767 报告头日期不覆盖 W768 追加 · GiB/GB 混用）**已逐条处置**。**新增判据**：(1) **KL 方向必须写死并在报告里声明**（`X vs Y` = `KL(Y\|\|X)`），非对称量不允许只写标签；(2) **同一标签在两个报告里出现时必须取自同一函数、同一参数顺序**（本次是 `cmp()` 两参数写反）；(3) 装 `tsv` 时"行数"与"唯一位置"是**两个数**，报告须分别给。 |
| 46 | **W773 发车 P46（io-预取族的 decode 面）+ 结论 `STRATA_IO_PREFETCH` = REJECTED（P54）**（2026-10-10 23:32 ~ 2026-10-11 00:12） | 机主令「按你计划据实办理」。**先把 `P46` 那条族行拆开**（四条不是一个东西）：`STRATA_IO_PREFETCH` = 唯一直接对口 decode（Linux file-tier I/O，未命中专家 + 下一层路由预测的专家改由 I/O 线程 whole-blob `pread` 预读，`DETAILS.md:223-227`；上游声明输出逐位相同）；`STRATA_FETCH_THREADS` 只作用于 GGUF-in-place 未命中装配（`expert_source.hpp:619`，默认 8，**同路径不组合测** W723）；`STRATA_FILL_AHEAD` 面向上线**填充**时间（Gen3 NVMe 70 s vs 920 s，**不对口 decode**）；`STRATA_FS_AHEAD` 只是 `STRATA_FS_SLOTS` 的子开关、而上游在每台机器上都把后者测成负的（0.91-1.00）=> **不单独测**。**启用前提**（`expert_source.cpp:564`）：Linux + mapped base + paths 可 open + `direct_` 为空（非 unbuffered）；且 `generate.cpp:4182-4188` **两个分支都打印** => 必须读启动行才知道生效与否。**发车**：4 臂交错 `A B A2 B2`，唯一改变量 = env 段加 `STRATA_IO_PREFETCH=1`（断言：A/A2 `[log,port]`、B/B2 `[env,log,port]` 且 env 只多一键、`args` 逐位不动）；负载 32768/128000 各 2 runs、max_tokens 256、每 run 新 nonce（`reused` 全 0）；`ARMS_FAIL=0`、pull 9/9。**机制证据（判据本体）**：引擎 `/proc/12` environ 含它 + 启动日志 `file tier io prefetch ON ... 8 I/O threads`；但**每请求 `io prefetch: 0 read ahead (0.0 MB by pread), 0 used, 0 unused, 0 skipped`（4/4 读数）** ---- 因为 `page cache held 78191.7 MB`、`the OS read 998.5 MB from storage for 42282.7 MB of expert reads`、启动行 `0.0 GiB of experts read from the files`。**三口径 ON/OFF 中位比**：`decode tok/s` 1.0013(32768) / 0.9469(128000)；`ms/offered 轮` 1.0597 / 1.0458；`ms/ckpt` 1.0410 / 1.0569；**臂内 spread 10-27%（`ms/ckpt` 达 132%）** => **读数不可判**（对照 W760 的 0.3% 噪声底：本车用不同 nonce 的不同文本、每格只 2 runs）。**判定**：`STRATA_IO_PREFETCH` => **REJECTED**（登记 **P54**）：收益前提在本机不成立（专家几乎全命中 page cache / RAM copy）---- **它不是"参数无效"（引擎确实 ON 了），而是"瓶颈不在 file-tier I/O"**。`P46` 保留 CANDIDATE（`FETCH_THREADS`/`FILL_AHEAD` 未测）。**新判据（本轮血证）**：**`运行期生效 != 实际动作`** ---- 只看"env 设了 / 日志说 ON"会把本条误判成"已生效、值得期待"；必须去读**该机制自己的动作计数**（`0 read ahead`）。这是既有判据「用户传参 != 运行期生效值」的**下一步**。期间核验器曾 EXIT=1，查明是**车在跑、生产容器停着**导致 `docker ps` 为空、核验器定位不到容器（**不是被改红**）；收车后复跑 **PASS=26 FAIL=0**。 |
| 47 | **W774：上游 v0.1.42 升级 + 读全 release notes + 登记 P55-P60**（2026-10-11 00:0x-00:4x） | 上游 main 自 10-08 前进到 **v0.1.42**（发布 2026-10-11 00:10 CST）。读全 23,126 字符 release notes + 逐 PR 核对：**我们 3 个 PR（#1731/#1732/#1733）全部被关闭并"with your authorship"合入 v0.1.42**（closed-not-merged = 维护者手工摘提交 + 署名，见 §6.3 更新）。新增**两条 gfx906 专属 opt-in**：`STRATA_GFX906_ATTN_QUERY_SWIZZLE`（#1661，作者 0FL01）+ `STRATA_GFX906_ATTN_REDUCE12`（#1718，依赖前者），上游逐字注明 **无 MI50 卡验证** => 登记 **P55/P56 = CANDIDATE**。另封口 **P57**（v0.1.42 非 gfx906 开关族，逐条 REJECTED 且注明理由）与 **P58**（通用新项 REFERENCE，含 `STRATA_PLE_PROBE` 的行为变化待核 + `tools/replay_cache_policy.py` 对口 W769）。register => **74 行数据**。构建镜像 `strata-gfx906:0.1.42`（6.59 GB，`PATCH_SURFACE_ZERO`）。见 `W774_UPSTREAM_0142.md`。 |
| 48 | **W774 发车：0.1.42 升级验证 + 四个 opt-in（P55/P56/P59/P60）**（2026-10-11 00:4x 首发，00:52 修 bug 重发） | 五臂 `p41`(0.1.41 基线) / `p42`(0.1.42 逐位) / `sw1`(+QUERY_SWIZZLE) / `sw2`(+QUERY_SWIZZLE+REDUCE12) / `hm1`(+HEAD_MIX_MULTI+ONE_TOKEN_COMMIT)。**首发血证**：arm 循环用 `:` 作分隔符，而镜像名自带 `:`（`strata-gfx906:0.1.41`）=> `spec##*:` 丢掉 `strata-gfx906` 前缀 => docker run 收到 `0.1.41:latest` 失败。**已改 `|` 分隔**。**并发血证（更严重）**：同一脚本被 `ssh nohup &` 与 `setsid &` **各启一份**，两者抢同一容器名 `w774_arm` 与端口 8095，且 `trap restore EXIT` 在对方被 kill 时**重启生产、删掉对方的臂容器** => 数据全部污染。**已加 `flock` 单实例锁 + `RESTORED` 幂等 guard**，清场后重发（唯一实例，锁获取已证）。**同时发现**：GitHub 写通道（GCM token）当前**不可用**（`git credential fill` 返回 prompt 文本、`GCM github list` 为空 => 需机主交互解锁一次），读通道（匿名 API）**完全可用**。 |
| 49 | **W774 收车 + 出结论 + 落账**（5 臂 / 20 条读数，`ARMS_FAIL=0`） | 收车 01:43:16，`[restore] HTTP=200` 生产恢复，`verify_config.py` **PASS=26 FAIL=0**。**先声明一个口径缺陷**：负载脚本 `filler()` 从**镜像自带的 `/src` 树**拼 prompt => p41(0.1.41) 实测 26036 tok vs p42+ 的 23781 tok（**小档 +9.5% 内容量，跨版本不可直比**；大档差 0.7% 可忽略）。**prompt 侧（主口径 `read_ms/read_tok`，干净可判）**：P55 `p42->sw1` 小 -0.00% / 大 -0.07%；P56 `sw1->sw2` +0.05% / +0.00%；P59+P60 `p42->hm1` +0.05% / +0.38% => **四个 opt-in 对 prefill 全部中性**；0.1.42 升级本身 prefill **无回归**（大档 -0.69% 在噪声内，小档 -3.36% 由口径缺陷解释）。**decode 侧弃权**：臂内 spread 达 16-21%（p41 小档 21.0%、大档 16.2%）> 全部组间差（-11%~+3.6%）；计数型（草稿接受率）在小/大档**符号反转**，无一致信号 => **二 runs 不足以判 decode**，需 5+ runs。**连带裁决**：(1) `STRATA_PLE_PROBE` 对生产**不可达**（生产 args 无 `--ple-io`/`--ple-gguf` => PLE 表未加载 => 探针路径从不执行；日志无 `PLE ... rows/s` 行）；(2) 修正两处机制（它是**抑制开关**、慢盘自动切 mmap 仅发生在**未显式给** `--ple-io` 时）；(3) **#1733/#1732/#1731 均已 ported**（源码核实 + `/metrics` 实读 `gpu_pcie_gen:3` `pcie_width:16`）；(4) **#1734 速率半未采纳**（0.1.42 `_Amd.read()` 仍无 `pcie_rx_mb`，只补 `pcie_path`）；(5) **#1735 上游未采纳但本机补丁已在生产运行**（`/metrics` 实读 `Radeon Instinct MI50 32GB`，FRU 原串是 `...16GB`）。register md5 `c28a7c89713a`（75 行数据）。见 `W774_UPSTREAM_0142.md` 第 7 节。 |

### 6.2 没做（原 12 项（W735 更正，原写 11）；**2026-10-09 20:4x W725 波后 => 仅剩 1 项**：#11 上游（机主令"先等等、之后一并弄"）。#5 / #7 / #10 / #12 **已于本波关闭**，见 `W725_SWEEP.md`）

| # | 事项 | 说明 |
|---|---|---|
| ~~1~~ | ~~**B7 / 新候选 P35 `STRATA_STAGER_SSD`**~~ **已完成 23:25**：三臂实测**无差**（<=0.1%）=> **#1353 对本机价值 = 0**，该开关无用；register 新增 **P98 = REJECTED** | 见 `deploy/tmp/_w713_b7_remote.log` |
| 2 | ~~**B3 P31/P33**~~ **P31 已关 2026-10-09 19:1x**（**P33 亦已处置 19:4x**：契约补齐为请求体顶层三写法、非法值 400；长文档 4 轮两臂**无增量**（该窗口 `evictions=0`；W735 更正）=> 保持 CANDIDATE。见 `W719_P33_PREFIX.md`） | P31：上游 parity 工具终审 = `PASS: A/B/A output and checkpoint reuse, byte-exact main-model state`（主模型状态逐字节一致）=> 已采纳：register **ADOPTED / 4096**，config 推 166 + `-407` 重启，`verify_config.py` **PASS=18 FAIL=0**；由此证明 W713 B3 的『两臂 md5 不同且互换』是**探针串位**。见 `W717_P31_PARITY.md` |
| 3 | ~~**B2 P23 `STRATA_PREFILL_CPU_SHARE`**~~ **已关 2026-10-09 19:3x** | 源码级：本机构建标记是 `STRATA_HIP_GFX906`、**不定义** `STRATA_USE_HIP`（compile_commands 计数=0），故 `prefill.cpp:1839` 的 `#if !defined(STRATA_USE_HIP)` 走 CUDA 分支 => `g_share_default=true` + 打 banner （**上游宏选择缺陷**）。实测两臂（CLI generate，4-token prompt）：默认 `on the CPU 197 (share 0.90)` vs `env=0` `on the CPU 0 (share 0.00)` => **机制真生效**，证伪官方 'AMD are as before'；但 prefill 928.3 vs 929.5 ms（差 0.13%，远低于分辨力）、输出逐 token 相同 => **零收益**。已采纳**显式 `=0`**（回到官方本意）。见 `W718_P23_CPUSHARE.md` |
| 4 | ~~**B6 P30 `STRATA_MMVQ_IL` 命中判定**~~ **已关 2026-10-09 02:0x** | 源码判定 = 本机结构上不可能命中（HIP 分支 `native_mmvq_il_supported()` 编译期恒 false）=> register P30 = **REJECTED（不适用）**；见 `W716_BASELINE.md` §1 |
| 5 | ~~**B4 P29 `STRATA_SPEC_GUMBEL`**~~ **已关 2026-10-09 20:3x**（机主令"据实判断"） | 据实：本服务**无采样用法**（config 无 sampling 段、`server.py:576` 默认贪心）=> 当前口径下**恒为空操作** => register **REJECTED**。与 P30 的区别：P30 是引擎层**结构性不可达**，本条是**用法层未触发**（非缺陷）；将来若引入 `temperature>0`，直接设 `=1` 即可。见 `W725_SWEEP.md` §1 |
| 6 | ~~**B5 P28 `STRATA_GR_SPLIT`**（同族 `--kv-grow`(P32)）~~ **已关 2026-10-09 19:4x** | 走「读源码即判、零发车」：P28 -> **REJECTED**（~3% < 解码分辨力 9.5-15%，且 'sums in another order' **破坏位一致**）；P32 -> **REJECTED**（上限 +93 槽 / +0.95%）。见 `W720_P28_P32.md` |
| 7 | ~~0.1.41 的 **#1454** 与 **tokenizer 缓存**两条~~ **已关 2026-10-09 20:3x** | #1454：源码算账（`prefill.cpp:252-256` 省 `T*N` floats per chunk；`N=2560` 由 pack 实证、我机 chunk=8192）=> **实为约 80 MiB（约 +35 槽 / +0.36%），非 320 MiB，且在分辨力下**；`STRATA_EMB_REUSE_ACCOUNT=1` 不采纳（改 rounding）。tokenizer cache：**隔离实测** ---- 105,826-token 文本重发 **0.109 s -> 0.054 s（-50.5%）且 ids 完全一致**（`tools/strata_tokenizer.py:211-233`，piece 级缓存，动机原文"an agent resends its whole history every turn"）。见 `W725_SWEEP.md` §3 |
| 8 | ~~**C4**~~ **已关 2026-10-09 19:1x** | `_sshutil.py` 已收进 `deploy/params/`（5464 B），两处改本地 `HERE`，运行期依赖归零；**顺带修掉 `gen_config.py` 的 `live_cfg()` 仍读 base 版旧文件名**（W715 切换漏改）；docstring 旧路径同步改；`gen_config.py --live` 自证『与 166 现行 config 无差异』。见 `W717_P31_PARITY.md` §3 |
| 9 | ~~**C5**~~ **已关 2026-10-09 19:1x** | `W709_HANDOVER.md` §4 新增两条（10764 -> 12136 B）：(1) 引擎启动行读 `/data/strata-*.log` 而非 `docker logs`；(2) 引擎级工具必须在容器内跑（宿主上 `cd /src` 静默失败，本轮实踩）。见 `W717_P31_PARITY.md` §4 |
| 10 | ~~**C3 旧镜像/容器清理**~~ **已关 2026-10-09 20:4x**（机主令"可以清"） | 走 `docker-disk-truth` 技能：**真账** ---- 5 张 strata 镜像名义 32.8 GB 但 `UNIQUE SIZE` 合计仅约 **2.74 GB**，而 docker 头条报 46.17 GB（**虚高约 15 倍**，差额为与他项目共享层）。**边界**：166 是共享机，只动 Strata 域（50 容器里大量 routeK / 服务容器，不碰）。**执行**：删 5 容器 + 4 镜像 + `builder prune -f` => **df 774G -> 771G（释放 3 GB）**、Build Cache 2.521GB -> 0；Strata 域终态 `-407`(Up)/`-406`(回滚位)/`0.1.41`。**实战复现坑**：删镜像后 df **不变**，层被 buildkit **重归类**到 Build Cache ---- 必须再 prune（技能 W646 判据再次验证）。**删前账本引用检查救场**：`configs/workbuddy-strata166.md` 把回滚写成 `start strata166-402` => 先改账本再删。见 `W725_SWEEP.md` §4 |
| 11 | **向上游提**（**对外件总账，2026-10-11 02:0x 并入机主对照表**）：<br>**#1396** PR 接收（ported）---- **仅编译验证、未跑过** -> 0.1.41<br>**#1731** PR 接收，署名 -> 0.1.42<br>**#1732** PR 接收，署名（**MI50 实测驱动**）-> 0.1.42<br>**#1733** PR 接收，署名 -> 0.1.42<br>**#1595** Issue **你赢了，改默认**（全驻留不武装）-> 0.1.42<br>**#1729** Issue **未认账**，待你补诊断数据 -> 0.1.42（加了内存保护）<br>**#1479** Issue patch 收为 opt-in，**co-author** -> --<br>**（W774 现查补充，与你表一致）** #1855 PR **仍 open / 0 回复**；#1734/#1735 Issue **仍 open / 0 回复**（无 label）。<br>**（见 `W736_PR_CANDIDATES.md` §7/§8 + `W774_UPSTREAM_0142.md`；原写"三件（2 PR + 1 feature request）"系 W724/W727 时代的计划，W736 实际交 **3 PR + 2 issue + 4 评论** ---- W752 审计 #13 指出两说。**2026-10-11 00:5x 现查**：3 PR #1731/#1732/#1733 全部 `closed`（**回执时间 2026-10-10 16:32:51Z / 16:32:57Z / 16:33:03Z**，即维护者同一分钟内集中处理完三件）且评论 "in v0.1.42 with your authorship"（**closed-not-merged = ported**，与 #1396 同模式）；2 issue #1734/#1735 **仍 open、0 回复**；4 条评论对应的 issue #1595/#1729/#1479 **维护者全已回复**，其中 **#1479 直接采纳我们的发现 -> v0.1.42 新增 `STRATA_HEAD_MIX_MULTI` / `STRATA_ONE_TOKEN_COMMIT` 两个 HIP opt-in（署名我们为 co-author）** => 登记 P59/P60） | (1) **PR #1732**（首选，1 行 bug）：`src/prefill/prefill.cpp:1839` 的 gfx906 宏判据漏判 => 维护者已按此合入 0.1.42（"The gfx906 build no longer takes the CUDA branch of arm_cpu_share, so the CPU share is not armed by default there"）。(2) **PR #1731/#1733** 同批合入。(3) **#1734/#1735 待跟进**（见 §6.4 #2）。(4) **#1670**（vizdatom layer-major prefill）：我们已在其下留言愿跑，**待移植到 HIP/gfx906**（见 §6.4 #3）。<br>(5) **#1595 与 #1729 是同一根因的两面**（现有标题逐字：#1595「0.1.41 CPU share default: no gain, and ~5% slower at 1,000 tokens」/ #1729「0.1.41: `STRATA_PREFILL_CPU_SHARE` on by default halves decode throughput」）：**#1595 我方论点成立 => 维护者改默认（全驻留不武装）**，即 0.1.42 的 gfx906 构建不再走 CUDA 分支的 `arm_cpu_share`（与 **#1732** 同一处修复：`prefill.cpp:1839` 的宏判据）=> **我们的 PR #1732 就是 #1595 的落地补丁**；**#1729 维护者未认账**（认为是环境相关、非普遍），**加了内存保护**，**待我们补诊断数据**。 |
| 12 | ~~**vision 段独立核验**~~ **已关 2026-10-09 20:3x**（机主令"你做"） | register V00-V02 与 config `vision` 段**逐字一致**；exe 实存 7,754,632 B sha256 `fadfa15a...`；mmproj sha256 `b1a82259...`；编码器 **pid 9 常驻**、argv 与 config 一致；`/v1/status` 报 **`vision:{enabled:true,available:true,error:null}`**；端到端图描述准确（"红色圆形位于中央 / 蓝色正方形位于左下"）。见 `W725_SWEEP.md` §2 |

### 6.3 重做（4 项）

| # | 事项 | 理由 |
|---|---|---|
| 1 | ~~**0.1.41 的解码基准（A2 的 0.1.41 分母）**~~ **已建 2026-10-09 02:1x**（并在 huihui 权重上重建） | 三档冷/温 + 两档追加式；两臂同批次对照 => 无退化。见 `W716_BASELINE.md` §2/§3 |
| 2 | 0.1.40.x 的其它读数若要引用需在 0.1.41 重取 | 闸门只复核了三档（100/220/530），其余档位未重测 |
| 3 | 0.1.40.1 时代的历史读数（预填 438.8 / 解码 42.9 tok/s） | **仅存档**，不得当现行基线 |
| 4 | ~~审计残余（PR #1396 徽章/提交哈希、166 侧下载来源、C-530 中位数）~~ **2026-10-09 20:4x 处置**（机主令"你定"） | **两项已做**：(1) PR #1396 实查 = `closed / merged:False`，但维护者评论"**is in 0.1.41 with your authorship kept** ... Closing as ported"、落地 commit `a732a19b6f` => 表述更正为"ported（非 merged）"；(2) 166 下载来源 = `build-ctx-411/transfer/{strata-src-0.1.41.zip, llama.cpp-3cf0325.tar.gz}`，166 侧无独立 sha256（旧波次靠两侧下载后对哈希）。**C-530 中位数不做**（属 0.1.40.x 历史读数，机主令"别弄了"）。见 `W725_SWEEP.md` §5 |

> **不重做、也不得引用的**：`waves/_w727.out.txt`（测试域无效：6,833-token prompt 短于一个 chunk）。

### 6.4 待办（W774 新增，2026-10-11 00:4x；**W775 追加 #15**，2026-10-11 04:1x）

| # | 事项 | 状态 / 前置 | 说明 |
|---|---|---|---|
| 1 | ~~**W774 五臂收车 + 出结论 + 落账**~~ **已完成 2026-10-11 01:43**（`ARMS_FAIL=0`，`verify_config` PASS=26；prompt 侧四组全中性、decode 侧弃权需 5+ runs；见 §6.1 第 49 条） | ~~在跑~~ **已关** | 判据：`p42 vs p41` = 0.1.42 升级无回归；`sw1 vs p42` = P55；`sw2 vs sw1` = P56；`hm1 vs p42` = P59+P60。**主口径 `ms/step`**（`tok/s` 受净出污染，W773 实测臂内 spread 达 27%），prompt/decode 两口径都报。收车后：跑 `verify_config.py`、写 `W774_UPSTREAM_0142.md` 结论节、按结论改 P55/P56/P59/P60 状态、跑 `mem_slim.py`。 |
| 2 | **跟进 issue #1734 / #1735**（我们开的，**仍 open**；~~"0 回复"~~ **W775delta 更正：两条各 1 条评论，但那 1 条都是我们自己发的 -- 不是维护者回复**） | **已回帖**（见 #13） | **#1734 的答案已经被维护者在 PR #1733 的回复里顺带给出**：他选了「**不填速率**、只补 `pcie_path`（读了多少 hop）」---- 源码核实 0.1.42 `_Amd.read()` 仍无 `pcie_rx_mb`/`pcie_tx_mb`，`link()` 新增 `pcie_path: "%d/%d"`。**#1735 的答案：上游未采纳**（`name()` 仍裸读 `product_name`），但**我们自己的补丁早已在生产运行**（`patches/serve-telemetry.py.patched`，`/metrics` 实读 `Radeon Instinct MI50 32GB` vs FRU 原串 `...16GB`）。**=> 两条 issue 的实际价值已兑现**（一条被部分采纳、一条我们有 local 解法）；**W775delta 实况（2026-10-11 04:3x API 现查）**：#1734 我方已回帖"不再要速率半"（`phoenixclyde` @2026-10-10T20:01:58Z）；#1735 我方已回帖指向所提 PR **#1877**（@20:02:04Z）=> **本条两个动作均已执行完毕，无遗留**。 |
| 3 | **评估 vizdatom 的 `perf-ryzen` 分支（#1670 layer-major prefill）** | 只读可做，跑测需移植 | 机制 = 对**未驻留专家**做 layer-major 预取以减 S/512 重读；与我们 **P33（pin）/ P46（io 预取）** 族相关，且 **P54 已证本机 file tier 非瓶颈** => 需判断其收益是否能兑现。**我们已在 #1670 主动留言愿跑**，但**未兑现**。**前置**：`STRATA_PREFILL_LAYER_MAJOR` 需先在本机 HIP/gfx906 上编译通过（其 base 是 0.1.39 + 10 commits）。 |
| 4 | **恢复 GitHub 写通道**（发评论 / 开 PR 用） | ~~阻塞中，需机主一次交互~~ **[已解决 2026-10-11：写通道已恢复 ---- `#1923`/`#1926` 两次 POST 均 201，`/user` 实读 `phoenixclyde`]** | **现查现证（2026-10-11 00:4x）**：`git credential fill` 返回的是 prompt 文本（89 B `Passwo...m': `）而非 token；`GCM github list` 输出为空 => GCM 凭据存储当前无 GitHub 凭据 / 未解锁。**读通道（匿名 API）完全可用**（本次查询全走它）。**解法**：机主在任意 git 操作（或 GCM 弹窗）里登录一次 phoenixclyde 账号即可恢复；之后 #2/#3 的写动作可自动完成。 |
| 5 | ~~**核 `STRATA_PLE_PROBE` 的升级副作用**（P58 派生）~~ **[更正 2026-10-14] 原判「对生产不可达」错（实为已在动作）** | ~~随收车核~~ **[重开] 转 `--ple-io direct` 对照车** | v0.1.42 新增启动时 PLE 探测：低于 15,000 rows/s 会把 `--ple-io direct` **自动切成 `mmap`**。我们生产 args **无 `--ple-io`（吃默认）** => 必须显式取证"升级后默认 PLE 路径是否变了"，而不是假定没变。**[本行原话正是这条纪律；W774/W750 后续却"假定了"，见 `W775delta_UPSTREAM_MAILCHECK_20261014.md` §E：实测 14,560 / 13,268 rows/s => 已被自动切 mmap]** |
| 6 | **补 #1729 的诊断数据**（维护者"未认账"，2026-10-11 02:0x 机主对照表新增） | **需写通道**（见 #4）；数据本身本机可复现 | 机主裁定：#1729（`STRATA_PREFILL_CPU_SHARE` 默认开导致 decode 腰斩）**维护者未认账、只加了内存保护**，**待我们补诊断数据**。**我们已有的素材**：**P23 已实测**（`W718_P23_CPUSHARE.md`）---- 本机宏判据 `STRATA_HIP_GFX906` 不定义 `STRATA_USE_HIP` => 走 CUDA 分支 => `g_share_default=true` + 打 banner（**上游宏选择缺陷**）；实测默认 `on the CPU 197 (share 0.90)` vs `env=0` `on the CPU 0 (share 0.00)` => **机制真生效**；但 prefill 928.3 vs 929.5 ms（差 0.13%，**低于分辨力**）、输出逐 token 相同 => **零收益**。**=> #1595 的"no gain"我方已证，但 #1729 的"halves decode throughput"我们尚未独立复现**（W718 只测了 prefill 面）。**动作**：写通道恢复后 (a) 在 #1729 贴出 `#1595 done` + 宏判据证据链；(b) 若要正面认账，需专门发一车测 **decode 侧**的 CPU-share 效应（默认 vs `=0`），给 `ms/step` + 臂内 spread。 |
| 7 | **#1479 patch 收为 opt-in 的连带核验**（2026-10-11 02:0x 机主对照表新增） | **[已完成 2026-10-11]**：用 0.1.42 源码树（`deploy/tmp/src142`）逐字核实 `verify.cpp:193-222` ---- HIP 默认关、`=1` 才开；上游注释自称 *bitwise the same sums*；见 `W775delta_SRC142_VERIFY.md` §2 | 机主裁定 #1479 = **patch 收为 opt-in，co-author**。我们已登记 **P59/P60**。**待核**：(a) 0.1.42 里 `STRATA_HEAD_MIX_MULTI`/`STRATA_ONE_TOKEN_COMMIT` 的 opt-in 语义是否与我们 PR 逐位一致；(b) **W774 五臂的 hm1 臂**已测过这对开关 => **prefill 全中性**（见 §6.1 第 49 条），**decode 需 5+ runs 才能判** => 这既是"已测"也是"待补"。 |
| 8 | ~~**生产容器升级到 0.1.42**~~ **已完成 2026-10-11 02:3x**（机主令"strata 必须更新到最新版"） | ~~在跑~~ **已关** | 动作链：备份 spec+config => `docker rename` 旧容器为 `strata166-407_0141bak`（**保留可回滚**）=> 用**同一 spec** 重建到 `strata-gfx906:0.1.42` => 就绪 => 重放 `patches/apply_telemetry_pcie.sh`（**必须**，否则写层丢失 MI50 name/PCIe tile）=> `docker restart` => 验收。**验收实测**：`/v1/status`+`/metrics` 双处 `engine:0.1.42`；容器 CMD 逐字与原一致；`gpu_name=Radeon Instinct MI50 32GB`、`gpu_pcie_gen=3`/`width=16`；真实推理 4.1s/40tok、`draft_n_accepted 25/27`；**`verify_config.py` PASS=26 FAIL=0**。见 `W775_VERSION_SYNC_0142.md` §4。**坑（已记）**：(1) 首建时把 CMD 作**单 argv 元素**经 ssh shell 串传 => 被按空格拆成 `["/bin/bash","-lc","cd","/src"]` => 容器 `Restarting(0)` 无日志空转；**修法=远端脚本走 base64->`bash -s` 通道 + `"$CMDSTR"` 双引号单参**。(2) 升级后须重放 telemetry 补丁。 |
| 9 | **P55/P56 在 0.1.42 上的复测**（新版同步派生） | * **W775delta 已定死靶：在现役 `k8v4` 下【主模型路径】不可达**（审计后收紧口径） | 上游 gfx906 社区报告 `bench/results/2026-10-08-gfx906-qsa-query-swizzle/`（2x Radeon Pro VII）实测 **`STRATA_GFX906_ATTN_QUERY_SWIZZLE` 组件侧 +14.646806%、整模型 +1.185% prompt / −1.049% latency、输出逐位相同**。**W774 五臂（sw1/sw2）prefill |delta|<=0.4% 中性** -> **W775delta 查明那是双重靶选错**：(1) 阶段错（四开关全在 decode/MTP 面，prefill 走 `qsa_prompt_attn.cu` 另一文件）；(2) **KV 格式错（本轮新证，`W775delta_W12_BANNER.md`）**。** banner 单变量对照（166，2026-10-11 05:07-05:14）**：`--kv k8v4` => `active=0 nq=32 cap=2051 kv_mode=3 lane_cell=0`（**不可达**）；`--kv int8` => `active=1 kv_mode=1`（可达）。**[!] 审计更正**：`k8v4` 那一行 **166 上无产物**（全盘 banner 命中皆为 int8 的 `active=1 kv_mode=1`）=> 该行 `kv_mode=3` 系**源码推演**，实测只兑现 int8 正对照；「主证 = 源码恒假，banner 仅旁证」。**根因**：`kv_mode` **不是 `--kv` 的字面映射**，而是从 pool 布局推得（`qsa_decode_attn.cu:626-627` 逐字**四分支** `kv_mode = pools.k_q4 != nullptr ? 2 : (pools.k_q != nullptr && pools.v_q4 != nullptr ? 3 : (pools.k_q != nullptr ? 1 : 0))` -- 原稿截断为 `: 1`，已更正）=> `k8v4` = hybrid（INT8 K + rotated Q4_0 V）=> **`kv_mode=3`**，而 `use_query_swizzle` 要求 **`kv_mode==1`**。**=> `P55`/`P56` 在生产 `k8v4` 的【主模型】上够不着**（要测只能在 `--kv int8`，但那是"换配方的收益"，不能算到 `k8v4` 头上；**drafter 侧理论可达但本波未观测**）。**`P59`/`P60` 与 KV 无关 => 靶仍成立，只发 D 臂**。**附**：banner 探针自身有 `thread_local` 一次性缺陷（`qsa_decode_attn.cu:644-646`），只能读"第一次调用的条件"，**可证伪不可证真**。见 `W775delta_W12_PRECHECK.md` + `W775delta_W12_BANNER.md` + `W775_AUDIT_delta.md`。**（补产物建议：重跑 `_w775_w12.sh B k8v4` 一次。）** |
| 10 | **评估 0.1.42 新增的 `replay_cache_policy.py`**（New opt-ins 命中） | [OK] **W775delta 已完整收车（源码面 + 实测面）** | 0.1.42 release notes 的 "New opt-ins" 段列出该工具件。**源码面已核**：工具族**三件在位**（`/src/tools/`，含 `bench_eviction.py` 四策略对拍 + `make_profile.py` + `routing_kfold.py`）。**原假设「与 P31/P34 重叠」证伪** -- 它测 **expert cache 淘汰策略**，与会话/KV 缓存不同模块；**引擎现状 = 从不淘汰**（`expert_cache.cpp:142-143` *"it never evicts"*）=> 无参数可拨。**实测面已跑（2026-10-11）**：trace = 3,838 positions x 48 层 x k=10 = **1,842,240 lookups**，9 档 slots x 4 策略 => **slots=9761 时 fill-only 0.7086 / lru 0.9751 / lfu-decay 0.9767 / oracle 0.9890**；slots=10327 时 fill-only 0.7517 / oracle 0.9903 => **命中率头部空间 +23.9~28.0pp（* 口径=命中率，离线复放，非 wall-clock），现成 LRU/LFU 可拿 ~95%**。**W13_REPLAY §4 的「<2pp 则判死」判据不成立 => P33/P41/P46 族不能判死（* 但 register status 本轮未动，三条仍 CANDIDATE，须另走重议）**。**发车三前置**：`--native SHARD1 --spec T(>=2) --prefill CHUNK` + `--ple-gguf <shard2>`。**教训**：`--dump-routing` 记录数由 `--max-new` **决定量级**（1024 => 3,838 positions => 184,224 条，非 1024x48）；`bench_eviction` 的 lookups = (layer,expert) 对数 != 记录数。**[!] 审计更正**：原稿「GPU cache 三数 9757/10327/9761」中的 **10327 实为 `bench_eviction` 手工入参、非引擎读数**（166 全盘无 `10327 in the GPU cache`）=> 撤回该「逐字」引用。详见 `W775delta_W13_RESULT.md`（源码面见 `W775delta_W13_REPLAY.md`；审计见 `W775_AUDIT_delta.md`） |
| 11 | **吸收上游 gfx906 社区报告**（新版同步派生） | 只读可做 | 上游 `bench/results/` 下已有多份 gfx906 报告。**已核**：我们的 **#1855 未被收录**；`2026-10-08-gfx906-qsa-query-swizzle` 已读（见 #9）。**待办**：把其余 gfx906 报告逐份读、与我们 register 的 P 编号逐条对齐，看有无**我们未登记而别人已实测**的结论（避免重复劳动/漏项）。 |
| 12 | **#1735 改提 PR**（机主令"2 可以提 pr"，2026-10-11 02:0x） | **需写通道**（见 #4，**已实际恢复**） | 原计划在 #1735 回帖贴 diff；机主改判为**直接提 PR**：把生产已运行的 `_Amd.name()` **FRU 容量一致性修正**（`patches/serve-telemetry.py.patched`，读 `mem_info_vram_total` 取整 GB 覆盖 `product_name` 里的容量串）抽成干净补丁，对上游提 PR。**前置**：先确认 0.1.42 的 `_Amd.name()` 仍裸读 `product_name`（§6.2 #11 (5) 已核）。见 `W775_VERSION_SYNC_0142.md` §6。 |
| 13 | **#1734 / #1729 回帖**（机主令"1 和 3 按你的来"） | **草稿 v3 已备，待机主过目** | **#1734**（速率半）：收口"we are not asking for the rate half any more" + 谢其 `pcie_path` 落地。**#1729**（CPU-share 腰斩 decode）：三段 -- (1)**主动更正**：我方 2026-10-09 那条**明说了只测 prompt 面**（928.3 vs 929.5 ms，差 0.13%，**在噪声底内**、输出逐 token 相同）=> 应被读作支持**武装半**、**不构成 decode 半的证据**；我方后续亦**复现不出** decode 损失；(2)**机制据实**：`prefill.cpp:1867-1876` 的守卫是 `#if !defined(STRATA_USE_HIP) && !defined(STRATA_HIP_GFX906)`，**0.1.42 才补上第二个合取项**（= 我方 PR **#1732** 标题逐字 *"the gfx906 build reached the CUDA branch of arm_cpu_share"*）=> 旧版落入 CUDA 分支 => `g_share_default=true`；0.1.42 我方**整块编译期不存在**；再加 #1595 的 `default_share_has_work` 与 H11 的 `share_default_ok()`；(3)我方**无与维护者结论相左**的补充，并提出可代跑复现。**两者草稿 v3**：`deploy/tmp/_w775_bodies_v3.py` => `_bodies_v3.json`（含幂等 marker `albus-checkin`），**待机主过目后再发**。见 `W775_VERSION_SYNC_0142.md` §4.5。 |
| 14 | **全量 PR/issue 状态复核**（机主令"看一下你提交的所有 pr 或者 issue 是否回复"） | **已完成 2026-10-11** | 匿名+token 实读 `Niko1221/Strata`：我方 **5 件** -- **#1877 open**（`mergeable_state: clean`，`serve/telemetry.py +16 -1`，**0 comments**，尚未被审）；**#1855 open**（MI50 32GB 262k bench，**未被 0.1.42 收录**）；**#1733 / #1732 / #1731 均 closed**（= 已并入 0.1.42；#1732 标题逐字揭示 0.1.42 的守卫修法）。=> **结论：除新提的 #1877 与仍挂的 #1855 外，其余全部 closed/merged，无"被回复但未处理"的悬空件**。 |
| 15 | **v0.1.42 changelog 全量合入待办主表**（机主令"你没有去看最新版的changelog和releasenote吗？之前不是让你合到待办的吗"） | **已完成 2026-10-11 04:1x** | 落点 = `W750_MASTER_PLAN.md` **§0.5（新增）**：按 W713 §1 三分法过全量 23,126 字符 => **(1)补丁面归零 3 条**（#1731/#1732/#1733，均已合入 0.1.42）、**(2)产生行动项 6 组 -> 新增 W12-W15**、**(3)无关封口（`P57`）**。同时刷新 §0.0 快照（引擎 `0.1.42`、`CANDIDATE 11` / `75 数据行`、三条评论已发、#1729 已改短版）、§1 行动项表（11->**15 条**）、§2 阶段（新增 P0'/P1''）、§7 上游关系、§8 指针。判据源 = `deploy/tmp/_rel0142.md`（UPSTREAM 原文）+ `W775_VERSION_SYNC_0142.md`。**注**：本波只**合表与刷新**，**未新增实测读数**；W12-W15 是**行动项**，非结论。 |


> **[BAN 归一说明 · 2026-10-11]** 本件属"活跃交付件"，已按项目禁用码位表（见 `W750_MASTER_PLAN.md` 第 0.5.7 节）做 **ASCII 归一**，映射：`U+2192`->`->` · `U+21D2`->`=>` · `U+2026`->`...` · `U+0394`->`delta` · `U+00D7`->`x` · `U+2014`->`--` · `U+2605`->`命中`/`*` · `U+2460-U+2469`->`(1)-(10)` · `U+2705`->`[OK]` · `U+26A0`->`[!]`。
> **引文处语义一字未改**，原文形态可回溯：改前副本 `deploy/tmp/_w21_bak/`（改前 md5 见件尾注）。
> 改前 md5 = `bf7e5afe93a274ae3c20dcc818bb6eb4`（字节 91206）。
