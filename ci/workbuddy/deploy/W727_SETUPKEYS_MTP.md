# W727 ---- 必备键清单 / api_monitor / PCIe / mtp.cpp:428 实测（机主令「据实处理」）

- 日期：2026-10-09 20:45 - 21:05（本机时间）
- 缘起：W726 留下的三个开口（`SETUP_KEYS` 必备键清单、`api_monitor` 开不开、PCIe 上游缺口）
  + 机主追问「`mtp.cpp:428` 这个你怎么处理了」+「回答我有多少 PR」。
- **本波四项全部处置完**：新增核验面 **2 个**（CFG 面 / SETUP_KEYS 覆盖面），`verify_config.py`
  **PASS=19 -> 24 FAIL=0**；`mtp.cpp:428` 由「待实测」变为**实测无差**。

---

## 1 必备键清单 ---- 核验器补了两个判定面（本波主线）

### 1.1 缺口是什么

W726 暴露的类缺陷：**`"backend": "hip"` 漏了整整 6 个波次**，逃过了 `verify_config.py`（当时 PASS=19 全绿）、
两轮独立审计、多次 config 对比 ---- 因为**它不体现在 args/env 里**，而 CFG 面此前一律 `SKIP`。
更糟的是：**没有任何判据在守 config 的「完整性」**（只守「已声明的项是否一致」）。

### 1.2 处置

**a) register 新增「必备键清单」7 行**（`scope=CFG`、`value=(不设)`、`status=REJECTED`，逐条写理由）：

| id | 键 | 上游消费点 | 不设的理由 |
|---|---|---|---|
| B01 | `lib_dirs` | `server.py:2363`（child_env，非空才改 LD_LIBRARY_PATH） | 容器默认已含 ROCm 库路径；缺省 = 不改 LD_LIBRARY_PATH |
| B02 | `gpu` | `:1846/2081-2083/2263-2266`、child_env 的 hip_visible | 单卡；缺省回落设备序，与显式等价 |
| B03 | `gpus_asked` | serve 全库 0 命中 | 仅 setup 簿记（`setup.py:1182/5473`） |
| B04 | `layer_split` | `:2127-2166/2328-2333` | 单卡，层切分不适用 |
| B05 | `api_key` | `:4533/5414-5415/5754-5758` | 实验台无鉴权（已知并接受的暴露面） |
| B06 | `draft_vocab` | serve 0 命中；`setup.py:4022/4085`（setup 期） | 缺省 `cjk` 与 Qwen 模型族一致 |
| B07 | `api_monitor` | `runconfig.py:35`（非 SETUP_KEYS） | 见 §2：Monitor 页不依赖它，且会把完整 prompt/答案留内存 |

**b) `verify_config.py` 新增数据面 (5)：CFG 面 + SETUP_KEYS 覆盖**

```
a. scope=CFG 且给了值 -> 必须与 LIVE config 逐字一致（V00/V01/V02/B00）
b. scope=CFG 且 value="(不设)" -> LIVE config 里必须确实不存在（B01-B07）
c. 上游 setup.py 的 SETUP_KEYS 全集 - (LIVE 实际键 ∪ register 已声明的 CFG 名) 必须为空
```

**关键设计**：SETUP_KEYS **从容器实时取**（`docker exec ... sed -n '/^SETUP_KEYS = frozenset(/,/})/p' /src/setup.py`），
**不写死在本脚本里** ---- 上游加键时本判定**自动跟上**，这正是「必备键清单」要防的那类静默漏项。

### 1.3 结果与自证

```
（数据面5）SETUP_KEYS 覆盖   17 键   PASS   上游 SETUP_KEYS 17 个全部有着落（config 实设 11 + register 声明 7）
PASS=24  FAIL=0
```

**判据非空性自证**（4 个反事实，全对 ---- 证明它真能抓漏，不是空判定）：

| 反事实 | 期望 | 实测 |
|---|---|---|
| 去掉 `backend` 且不声明 | 报 `backend` | `['backend']` PASS |
| 去掉 `backend` 但保留声明 | 免责为空 | `[]` PASS |
| 上游新增一个我们没设也没声明的键 | 报出 | `['some_new_key']` PASS |
| 删掉 `lib_dirs` 的声明行 | 报出 | `['lib_dirs']` PASS |

**config 未变**（`gen_config.py --live` = 「无差异」）---- 7 行都是 `(不设)`，不写入；`gen_config.py` 也加了
占位值防呆（`value` 以 `(` 开头的 CFG 行一律跳过）。**未重启服务**。

### 1.4 顺手抓到的**同类第 4 次**：技能工具的 BAN 清单缺了本项目 6 个码位

**现象**：`MEMORY.md` §3 里写着 `**「默认关」U+2260「不可达」**` ---- `U+2260`(U+2260) 正是本项目 §1 铁律的**禁用码位**，
而**适配版技能的 `VERIFY = OK` 一路放行**。

**根因**：`deploy/tools/mem_slim.py` 的 `BAN` 沿用了 **routeK 的清单**（箭头 / 带圈数字 / 星标 / emoji，30 个）；
本项目铁律的 10 个码位里，它只覆盖 4 个（`21D2` / `2192` / `2265` / `2264`），
**缺 6 个**：`2014`（破折号）/ `2013` / `2026`（省略号）/ `2260`（不等号）/ `2212`（减号）/ `00D7`（乘号）。
=> 「走技能」这个动作**没能守住本项目自己的规则** ---- 与 §1.1 的「CFG 面无人守」是同一类（**判据覆盖面不足**）。

**处置**：`BAN += [0x2014, 0x2013, 0x2026, 0x2260, 0x2212, 0x00D7]`（两边取并集，只增不减）。
- `py_compile` 通过；与 W727 前相比 `difflib` 逐行 diff = **16 行**（4 行新增 + 6 行修改，全在 BAN 处与工具自身的残留码位）
- BAN **30 -> 36** 个；`all(本项目 10 个 in BAN) = True`
- 本次落盘即把 §3 那个 `U+2260` 改成 `不等于`（`U+2260` 从 `MEMORY.md` 消失）
- 顺带清掉**工具自身**残留的 11 个禁用码位（注释里 10 个 U+2014 + 截断标记 `'...'` 1 个），工具现 `BAN=0`、`check` = `VERDICT OK`。
  ⚠ 那个 `'...'` 原本会写进被压文本 => **被工具自己的 BAN 断言拦下**（fail-closed，故不是漏网），但属隐患，已改 `'...'`。

> 同族前三次：W713 审计的**容器名硬编码**、W718 的**核验器 ENV 面缺口**、W726 的**CFG 面全 SKIP**。
> **共性都是「判据覆盖不到」而非「判据写错」** ---- 这个项目里，缺陷几乎总是死在覆盖面上。

---

## 2 `api_monitor` ---- 据实判定：**不设**（先证伪了「Monitor 页需要它」）

机主把这项交给我定。**我没有凭印象定，先做了实验**：

发一个真实 chat 请求，再读 `/metrics`：

```
requests_kept = 1
requests = [{..., prompt_tokens:58, reused:0, output_tokens:40, decode_tok_s:25.8,
             prompt_ms:1107.5, hit_rate:0.667, pcie_share:0.028, ...}]
```

**结论：Monitor tab 的「recent requests」表本来就能用**，它来自 `self.history`
（`server.py:2634` `deque(maxlen=500)`，`:3685` **无条件** append）---- **与 `api_monitor` 无关**。
W726 时它显示 "No requests yet"，只是因为**重启后还没发过生成请求**（不是缺开关）。

而 `api_monitor` 的真实作用（`server.py:2631/3040`）是**额外**把**最后 100 个请求的完整 prompt 与答案**留在内存，
服务启动时自己都会警告：

> `API request monitor on (/api-monitor): the last 100 requests' prompts and answers are kept in memory;
> anyone who can reach this server can read them (no API key)`

**判定：不设。** 三条理由：① Monitor 页不依赖它（已实测）；② 本机**无鉴权**（B05），开了等于把
prompt/答案放在局域网可读的内存里；③ 需要请求级取证时**临时开**即可（改 1 个键 + 重启），不必常开。

---

## 3 PCIe 卡片 ---- 上游缺口（**不自行修**）

`telemetry.py:97-103` 只在 **`_Nvml`** 分支读 pcie；`_Amd.read()` **完全没读**，而 amdgpu 的 sysfs 明明有
（`current_link_speed = 16.0 GT/s PCIe` / `current_link_width = 16` / `pcie_bw`）。

**为什么不自己修**：它在 `serve/telemetry.py`，属**镜像内**的 Python 件；改它 = 重新引入**补丁面**
（我们刚在 0.1.41 把补丁面归零）。=> **列为上游候选 2**，进将来那个批次。

---

## 4 `mtp.cpp:428` ---- 单变量实测：「待实测」变「实测无差」，**不提 PR**

### 4.1 开关本体（源码）

```cpp
:428  #if !defined(STRATA_USE_HIP)              // 非 HIP（含 gfx906） => 创建 side_ / sh_fork_ / sh_join_
:862  //  (CUDA; HIP keeps one stream: STRATA_MTP_SHARED_BRANCH=0 does too)
:863  static const bool branch_on = [] {
:864  #if defined(STRATA_USE_HIP)
:865      return false;
:866  #else  getenv("STRATA_MTP_SHARED_BRANCH"); return v == nullptr || atoi(v) != 0;   // 默认 true
```

我们的构建**不定义** `STRATA_USE_HIP`（与 P23 / P28 同一份宏证据：`compile_commands.json` 里只有
26 处 `-DSTRATA_HIP_GFX906`，`STRATA_USE_HIP` 计数 = 0）=> **gfx906 上该分支默认开**，
与 `:427` / `:861` 注释写的 "(CUDA; HIP keeps one stream)" **不符**。
`side_` 的创建与使用**用同一个宏** => 配套自洽，不会崩（W725 已判）。

**所以要动的只有一件事：这个「默认开」在 gfx906 上到底有没有影响。** 这正是 `STRATA_MTP_SHARED_BRANCH` 能回答的。

### 4.2 实测（A/B/A 顺序对照；单变量）

- 独立容器 `strata-mtp428` / `-428b` / `-428c`，**同一镜像与同一 config**，端口 8095，`--entrypoint` 直起 serve
- 每臂 **6 次**同 prompt、400-token、贪心；温态 = `reused>0` 的 5 次
- 引擎 `/proc/<pid>/environ` **实读**确认两臂 env 已生效（A/C 无、B=`STRATA_MTP_SHARED_BRANCH=0`）
- MTP 真的在跑：`/metrics` 的 `drafts_offered > 0`（每臂 1371~1443），日志 `strata mtp: draft layer loaded, 1098 MiB`

| 臂 | 分支 | 温态 decode t/s（5 次） | 均值 | **中位** | 接受率 |
|---|---|---|---|---|---|
| A | **开**（默认） | 45.2 / 45.8 / 46.7 / 47.2 / 48.8 | 46.74 | **46.7** | 1143/1418 = 80.61% |
| B | **关**（`=0`） | 42.6 / 43.4 / 46.3 / 47.9 / 48.1 | 45.66 | **46.3** | 1088/1371 = 79.36% |
| C | **开**（默认） | 44.6 / 45.3 / 45.8 / 46.8 / 49.0 | 46.30 | **45.8** | 1156/1443 = 80.11% |

**噪声底**（同为默认档的 **A 与 C**）= **0.94%**；`A vs B = -2.31%`、`C vs B = -1.38%`
---- **全部在解码分辨力 9.5~15% 之下**；而且按**中位**看 `B(46.3)` **恰落在两个默认档 `A(46.7)` 与 `C(45.8)` 之间**
=> **无可辨差异**。接受率差 1.25pp，同为噪声。

### 4.3 处置

**不提 PR。** 三条理由：
① 实测无影响（在分辨力下）=> 改代码**没有依据**；
② 若只照「补 `&& !defined(STRATA_HIP_GFX906)`」去改会**只关创建、不关使用** => 引入 `side_ == nullptr` 的**真 bug**
（W725 已判；要改必须 `:428` 与 `:862` 同时改，属「一处改动两处落」的高风险改法）；
③ 它不构成行为缺陷（输出口径无异常）。

**留档方式**：作为「上游第 3 处宏判据不一致（`:420` 认 gfx906，`:428/:862` 不认）」的**观察**，
将来提上游时可以附在 issue 里当一句说明 ---- **不单独开 PR**。
结论已落 register **P35 `STRATA_MTP_SHARED_BRANCH` = REJECTED（保持默认不设）**，附全套读数，免得日后重测。

---

## 5 上游 PR 总账（回答「有多少 PR」）

| # | 类型 | 位置 | 体量 | 状态 |
|---|---|---|---|---|
| 1 | **代码 PR（首选）** | `src/prefill/prefill.cpp:1839` 宏判据漏判 | **1 行** | 待提（机主令「先等等、之后一并弄」）；证据链最硬：上游自己在 `core/mtp.cpp:420` 相隔 9 行处写对了 |
| 2 | **代码 PR** | `serve/telemetry.py` `_Amd.read()` 补 PCIe 读数 | 约 4-6 行 | 待提（W726 发现；sysfs 有数据、代码没读） |
| 3 | **feature request（issue）** | 让可复用 checkpoint 落在**子 chunk 边界**而不改 prefill chunk | 提案 | 待提（B1b 派生；属「重复计算类」，按 W721 规律才是下一个两位数） |
| -- | **只观察，不提** | `mtp.cpp:428/:862` 宏判据不一致 | -- | 本波实测无影响 => 附在 issue 说明里 |
| -- | **历史（已完结）** | PR **#1396**（gfx906 构建修复） | 已落地 | **ported 进 0.1.41 且保留署名**（commit `a732a19b6f`），PR 本身 `closed-not-merged` |

**=> 要对外提的共 3 件：2 个代码 PR + 1 个 feature request。**
通道已备好：`166:pr/strata-fork`（真 git 仓，remote `git@github.com:phoenixclyde/Strata.git`）+ `_mkpr.sh`。

---

## 6 落盘

| 件 | 变动 |
|---|---|
| `deploy/params/PARAM_REGISTER.tsv` | 新增 **B01-B07**（必备键清单）+ **P35**（MTP 分支实测）；**49 行 / ADOPTED 23 / REJECTED 25 / CANDIDATE 1**；两侧 md5 `5a9a74f0...`；备份 `.bak_w727_*` / `.bak_w727b_*` |
| `deploy/params/gen_config.py` | CFG 占位值防呆（`(` 开头不写）；备份 `.bak_w727_*` |
| `deploy/params/verify_config.py` | 新增数据面 (5)：CFG 面 + SETUP_KEYS 覆盖；`parse_setup_keys` / `cfg_lookup`；docstring 五面；备份 `.bak_w727_*` |
| `deploy/params/generated/*.json` | **未变**（`--live` 无差异） |
| `deploy/tools/mem_slim.py` | **BAN 清单补齐**（30 -> 36，并入本项目 6 个码位）**+ 清掉工具自身残留的 11 个禁用码位**（注释里的 10 个 U+2014 + 截断标记的 1 个 U+2026）；备份 `.bak_w727_*` / `.bak_w727c_*`；md5 `6ad9dd2f...`；`py_compile` rc=0、`check` = `VERDICT OK` |
| `.workbuddy/memory/MEMORY.md` | 走技能 `auto`：**2849 -> 2890 chars**、余量 10、md5 `61ec2707...`；归档 `Z-8`；`U+2260` 已清除；新增铁律 1 条 + §4 上游件 1->3 |
| `deploy/tmp/_w727_out_{A,A2,B,B2,C,C2}.json`、`_w727_arm{A,B,C}.log`、`_w727_client.py`、`w727_mtp428_summary.txt`、`_w727_mtp428_evidence.txt`、`w727_mtplines` | MTP 分支三臂原始证据 |
| `deploy/W727_SETUPKEYS_MTP.md` | 本件 |

**166 终态**：`-407` Up（45 s 就绪）、HTTP 200、`verify_config.py` **PASS=24 FAIL=0**；
三个临时容器（`strata-mtp428{,b,c}`）**已删**；`data/` 里的 `_w727_*` 临时件**已清**（`ls | wc -l` = 0）；
`-406` 仍是回滚位。

> 本波踩的坑（如实记）：取回证据时按「行首 marker」切分，而 `json.dump` **不写结尾换行** =>
> 下一个 `echo marker` 被粘在同一行，marker 认不出、多个件被并成一个。**内容未丢**（marker 在文本里），
> 改按「出现位置」切分即复原。=> 教训：**多个文件走同一条 stdout 通道时，先给每个文件补一个结尾换行再打 marker**。
