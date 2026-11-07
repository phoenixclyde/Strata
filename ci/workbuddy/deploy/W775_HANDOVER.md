# W775_HANDOVER ---- 会话交接（W775delta 收车，2026-10-11 05:3x）

> 用途：把 W775delta 这一波的状态移交给新会话。
> 上游状态看 `deploy/W750_MASTER_PLAN.md`（唯一合并表）；运行期机制看 `PROJECT.md`；迁移史看 `HANDOVER.md`。
> 本件是**单时点现算的干净版**（不累积校正块）。全部数字现场现取，无转述。

---

## §0 新会话开工

### 第一条指令（可直接粘贴）

```
接手 Strata 项目（W775delta 之后）。工作区 D:/workbuddy_space/strata_ws/。

第一动作：按序读这五份，再查技能清单
1. PROJECT.md（自包含入口）
2. .workbuddy/memory/MEMORY.md（长期记忆，注意它超窗，见 §7 坑）
3. deploy/W750_MASTER_PLAN.md（唯一合并待办表；§0.0 = 现时点执行版）
4. deploy/W775_HANDOVER.md（本件）
5. .workbuddy/memory/2026-10-11.md（本日流水，含 W775delta + 审计段）

然后 Load 技能：改参数走 register 通道；发车/审计/记忆压缩各自有技能，先加载再动手。

三条不可越的边界：
- 改参数唯一通道：register -> gen_config.py --write -> 推 166 -> restart -> verify_config FAIL=0
- 引用任何性能读数必须带 Z0=off
- 发给外部的任何内容（含 GitHub）先给机主过目；不要用 present_files
```

### 开工三步

1. **现场复核**（不要引用本件数字，现跑）：
   ```bash
   # 本机跑（Python subprocess + base64 通道；ssh 单引号形式会被 shim 打坏）
   docker inspect -f '{{.State.Running}}' strata166-407     # 期望 true
   curl -s -m 5 -o /dev/null -w '%{http_code}\n' http://127.0.0.1:8090/v1/models   # 期望 200
   ```
2. **读 `W750_MASTER_PLAN.md §0.0`**拿现时点快照（它比本件更新节奏快）。
3. 按 §4 未闭环项**第一项**推进。

---

## §1 一句话

Strata（gfx906/MI50 32GB 单卡推理引擎）在 166 测试台上的**部署 + 调参**项目。
判据四条：**同形状 / 只比 ms/step / 带 Z0=off / 冷温不混比**。

---

## §2 当前态快照（2026-10-11 05:30 现算）

### 2.1 权威件指针（全部现读，含 md5）

| 件 | 字节 | md5 |
|---|---|---|
| deploy/params/PARAM_REGISTER.tsv | 80,886 | 151e493a27f4621190581a8e89607165 |
| deploy/W750_MASTER_PLAN.md | 38,497 | 0a0d1941e28a31632f70cf836d095b9e |
| deploy/W713_PLAN.md | 90,873 | dc7b05bd3d3a1998136d108281830611 |
| deploy/W775delta_W13_RESULT.md | 11,440 | 13d67200a4031ad573567da5b1a0668f |
| deploy/W775delta_W12_BANNER.md | 12,448 | 467aace36951ef3e350d478cef5b1f74 |
| deploy/W775_AUDIT_delta.md | 18,344 | 386ef51296bbd29256be94133c011fd5 |
| .workbuddy/memory/2026-10-11.md | 85,709 | 6fd795ab647a613077124bb550f8b1ee |

> **[!] 快照说明（2026-10-11 14:3x / 14:5x 两次追加）**：本表是 **2026-10-11 05:30 的时点快照**（`W750` · `W713_PLAN` · `W13_RESULT` · `W12_BANNER` · `AUDIT_delta` · 日志 · `REL0142_LEDGER`），**按其自身规则「引用前现算、别照抄」**。其后变更：(a) `W13_RESULT.md` 追加「口径限定」（`fill-only 0.7086` 为 trace 口径、非生产口径）；(b) **`W21` BAN 归一（2026-10-11 14:4x-14:5x）**：本表所列各件（日志除外）**均做 ASCII 归一**（禁用码位 -> 0），=> **除日志外各行字节/md5 已全部失效**。**现值一律现算**；每件尾部记有「改前 md5」，`deploy/tmp/_w21_md5map*.txt` 存旧->新映射，`deploy/tmp/_w21_bak/` 存改前副本。
| deploy/W775delta_REL0142_LEDGER.md **（补录 2026-10-11 11:2x）** | 21,405 | 97e577525b932a92b5adbf9e27c69e63 |

> 全部 `CR=0`（纯 LF）。**引用前现算**（`md5sum` + `wc -c`），别照抄本表。
> **补录说明**：`deploy/W775delta_REL0142_LEDGER.md`（v0.1.42 changelog 逐条台账，64 行 / 命中 12、通用 19、不适用 33）**交接时漏列**，本会话补入（同一行的 `W750 §8` 早已收录）。其余各行仍是 05:3x 的现算值；其后如有改动，以 `W750_MASTER_PLAN.md §0.5.4` 的更正清单为准。

### 2.2 现役指纹（照抄即可发车）

| 项 | 值 |
|---|---|
| 引擎版本 | **0.1.42**（上游 `Niko1221/Strata`） |
| 引擎 md5 | `5efa1d45c2e8c6f14b62a96b32d03155`（`/src/build-906/strata`） |
| 镜像 | `strata-gfx906:0.1.42` |
| 容器 | `strata166-407` @8090，`Up`，`--restart unless-stopped` |
| 生产 config md5 | `6261ddf8a81bf0ebe90101d3b0cf8455`（`data/strata-huihui-ud-iq4_xs.json`）**[!] 2026-10-11 17:37 起现况 = `ff8cb97379f0bdbe76ee555da6d8729c`（W4x-B7 固化；本表为 05:30 时点快照，引用前现算）** |
| 回滚位 | `strata166-407_0141bak`（0.1.41，Exited）/ `strata166-406`（Exited） |
| 模型 | `qwen3.8-flash-next-ud-iq4_xs`（huihui），262144 上下文，`--kv k8v4` |
| 核验 | `verify_config.py` PASS=26 FAIL=0 · HTTP 200 |
| 补丁面 | 引擎 0 / serve 覆写 2（telemetry + app.js，**重建容器须重放 `apply_telemetry_pcie.sh`**） |

### 2.3 生产启动命令（逐字，来自 166 `ps -ef`）

```
/src/build-906/strata --serve --pack /data/packs/huihui-ud-iq4_xs
  --native /models/huihui-ai/Huihui-Qwen3.8-Flash-Next-abliterated-GGUF/unsloth-UD-IQ4_XS/Qwen3.8-Flash-Next-UD-IQ4_XS-00001-of-00003.gguf
  --resident-budget-gib 76 --expert-profile /src/data/expert-profile.bin --expert-cache auto
  --pcie-frac 0.20 --spec 4 --spec-min-p 0.70 --mtp /data/mtp/rt --max-context 262144
  --kv k8v4 --prefill auto --prompt-cache-every 8192
  --expert-profile-save /data/profiles/huihui-ud-iq4_xs-learned.bin
  --conversation-cache-mib 4096 --vision --mtp-window 8192
```

### 2.4 register 现状（现算）

75 数据行 / 11 列 · `ADOPTED 26 · REJECTED 32 · CANDIDATE 11 · REFERENCE 6`（sum 75 · 无重复 ID）。 **补录（2026-10-11 11:5x）：W12D 后 `P59`/`P60` -> REJECTED => 现况 `26 / 34 / 9 / 6`，sum 75 不变。**
CANDIDATE = `P33`·`P97`·`P41`·`P42`·`P46`·`P47`·`P48`·`P55`·`P56`（9 条；**补录 2026-10-11**：`P59`·`P60` 已判 REJECTED）。

---

## §3 最近几批结论（W775 族）

| 批 | 账本落点 | 一句话 | 关键限定 |
|---|---|---|---|
| **W13 实测**| `W775delta_W13_RESULT.md` | expert-cache 策略矩阵：fill-only 0.7086~0.7517 vs oracle 0.9890~0.9903 | **命中率口径，非 wall-clock**；离线复放；`W13_REPLAY §4` 的「<2pp 判死」**判据不成立**|
| **W12 banner**| `W775delta_W12_BANNER.md` | `P55`/`P56` 在 `k8v4` 下**主模型路径**不可达 | **主证 = 源码 `kv_mode==1` 恒假**；banner 仅旁证（k8v4 侧无产物）；**drafter 侧未观测**|
| **W775delta 审计**| `W775_AUDIT_delta.md` | 独立子 agent + 本机复核：**2 P0 / 5 P1**，已全部修正 | 矩阵 35/36 格相符；数字台账两处 P0 |
| W774 五臂 | `W774_UPSTREAM_0142.md` | P55·P56·P59·P60 **prefill 全中性**| decode **弃权**（臂内 spread 16-21%，需 5+ runs） |
| W775 升级 | `W775_VERSION_SYNC_0142.md` | 生产升 0.1.42，净修复零回归 | 回滚位 `-407_0141bak` |

---

## §4 未闭环项（按顺序，预注册下一批）

1. **W12 D 臂**（A 基线 / D=P59+P60）x decode `ms/step` x 5 runs ---- **靶仍成立**（与 KV 无关）。
   - **前置**：`W775delta_W12_PRECHECK.md`。**注意**：本次两车都是 `--max-new 8`、无 `--vision/--mtp/conv-cache`
     => `STRATA_HEAD_MIX_MULTI`/`STRATA_ONE_TOKEN_COMMIT` 路径**未启用**；D 臂必须在**生产同构**环境跑。
   - **为什么现在做**：P59/P60 是 0.1.42 新项里**唯一靶仍成立**的，W774 已弃权，只有它能出结论。
2. **▲ W12 k8v4 补产物**（审计新增）：重跑 `bash /home/albus/strata166/_w775_w12.sh B k8v4`
   => 把 P0-3「k8v4 banner 无产物」消掉（一次停-起，~40 s 恢复）。
3. **W13 下一步**：核上游 `expert_cache.hpp:11` 提到的 R4.1 **LFU-decay vs LRU sweep**是否已有实现 / 是否可提 feature
   （我们有 9 档 x 4 策略实测矩阵支撑）。**不开车**，只读源码 + 查上游 issue。
4. **W6 §4 族其余**（`P41`，12 个只测过 2 个，**必须逐个串行**）· **W7**`--lookup-chain`（`P42`）。
5. **W4 逐桶账**· **W8**`kShape` 标定 · **W9**并发面（须先重议 `P97`）。
6. **W11 上游跟进**：#1855 / #1877 仍 open；**#1729 待补诊断**（维护者点名要三样：
   `prefill:`/`on the CPU N (share X)` 行、Task Manager 内存、**只改 `STRATA_PREFILL_CPU_SHARE=0` 的干净对照**---- 注意本机已**长期 =0**，故「干净对照」需另设计）。
7. **`P46`/`P47` 族**（`P46` 的 IO_PREFETCH 子项已测 = `P54 REJECTED`）。

---

## §5 待裁定清单

### 本轮新产生

| # | 事项 | 现状 | 我的建议 | 为什么不自己决定 |
|---|---|---|---|---|
| 1 | `P33`/`P41`/`P46` 族是否重议（W13 证明天花板是 24-28pp 不是 2pp） | 三条仍 CANDIDATE，**未动**| 重议后按新判据定 | 改裁定属机主签字项 |
| 2 | W12 `P55`/`P56` 是否 **直接判「k8v4 不可达」**| 仅 verdict 尾注，`value` 已标「在 k8v4 下不可达」 | 判「主模型路径不可达」，drafter 侧留观察 | 口径（全机 vs 主模型）属机主裁定 |
| 3 | W12 是否**另立 `--kv int8` 车**测 P55/P56 | 未立 | 若目标是评估 `--kv int8` 才立；否则不立 | 属目标口径问题 |
| 4 | W13 是否**向上游提 feature**（淘汰策略） | 未提 | 先读上游有无实现，再决定是否提 | 发上游内容须机主过目 |
| 5 | **全工作区禁用码位**（1,731 md 里 488 个含、共 11,089 处） | 规则写着但从未全库执行 | 只对活跃交付件执行 + 历史件冻结；或调整规则只约束新产出 | 涉及批量改写 488 个权威/历史件，且与「历史件逐字保留」冲突 |

### 沿用（仍有效）

- **改参数唯一通道**：register -> `gen_config.py --write` -> 推 166 -> restart -> `verify_config` FAIL=0。
- 引用任何读数带 **`Z0=off`**；`verify_config` 只判配置面，运行期须另取引擎 `/proc`（W764）。
- **发给外部的内容先给机主过目**（含 GitHub PR/issue/回帖）。

---

## §6 现场状态（2026-10-11 05:30 现算）

### 166

| 项 | 值 |
|---|---|
| date / uptime -s | 2026-10-11_05:30:32 / 2026-10-06 12:24:24 |
| 常驻容器 | `comfyui-cu130`·`netdata`·`open-webui`·`portainer`·`searxng`（各 Up 4 days）+ `strata166-407`（Up 16 min） |
| 我方残留 | **0**（无 w775/w12/w13/dump 容器；`rocm-smi` 只有生产 `4193230 strata`） |
| 生产 | `strata166-407` = true · HTTP 200 · 引擎 md5 `5efa1d45...` |
| Exited 回滚位 | `strata166-407_0141bak`（0.1.41）· `strata166-406`（0.1.41）· 大批 `rk_w680_*`（routeK 遗留） |
| 磁盘 | Images 43/65.04GB（可回收 46.17GB）· Containers 46/7.73GB（可回收 7.54GB） |

### 本机

| 项 | 值 |
|---|---|
| 监听 8800-9000 | **0**（无残留临时服务；历史上 8899 出过残留事故） |
| 后台任务 | 无（本轮所有 ssh/车均已收口） |

---

## §7 环境与工具铁律（本机缺陷，逐条可照做）

1. **Bash 工具长期损坏**：`dirname`/`cd`/`head`/`tail`/`ls`/`wc`/`grep`/`cat`/`cp` 全缺
   => 一律用**绝对路径 Python**`C:/Users/clyde/.workbuddy/binaries/python/versions/3.13.12/python.exe`；
   文件操作走 Read/Write/Edit/Glob/Grep。
2. **ssh 一律用 Python `subprocess.run(["ssh", ...argv])`**（argv 不经 shell）；直接写 `ssh '...'` 会被 shim 打坏
   （报 `banner exchange: Connection to UNKNOWN port -1`）。
3. **远端脚本先 base64 再发**：`base64 -d | bash`（防 shim 吃行首字符 + CR/LF 翻转）。
   **input 传 bytes 不传 str**（text=True 会翻 CRLF => 远端报 127）。
4. **含中文 / 反引号 / `$(` 的落盘一律用 Write 工具直写**（不经 shell、不经 PS 管道）。
   远端双层 base64 会互相破坏 => 用 `printf '%s' <b64> > /tmp/x.b64 && base64 -d /tmp/x.b64 > target`。
5. **Python 脚本含长 markdown / 三引号串时不得走多层 ssh 转义**=> 用 Write 在本机写好，再 base64 上传。
6. **改既有长件前先备份**（register/config/verify_config/日志）。
7. **改本件（MEMORY.md）走技能入口**（`routek-memory-slim` / `mem_slim.py`），**禁 Edit 挤牙膏**。
   ---- **注意：`.workbuddy/memory/MEMORY.md` 现 4,212 B，已超 3,000 字符注入窗 => 开工第一件事应压回窗内。**
8. **禁用码位**：只用 ASCII + 汉字 + 基本中文标点；禁 emoji / 带圈数字 / `U+2026`/`U+0394`/`U+2192`
   （用 `...` / `delta` / `->`）。交付件须 `CR=0`。
9. **不要用 `present_files`**（机主：交付物只在正文给路径）。
10. **临时/后台任务用完即停**（本项目因残留 HTTP 服务出过事故）。

---

## §8 踩过的坑（最值得继承的，每条带实例）

1. **「实读」不许写成「逐字」---- 引用源码要把整条语句（含跨行续行）读全。**实例：`qsa_decode_attn.cu:626` 我引作 `... ? 3 : 1)`，实为**四分支跨两行**`... ? 3 : (k_q ? 1 : 0))`。
   为省字节截断三元式 = 把「逐字」变成伪造；**本次 4 处扩散**（一处错跟着复制到 BANNER/register/memory）。
2. **工具入参不是实测读数。**实例：`bench_eviction --slots 10327` 的 10327 是**我选的**，
   原稿写成「日志逐字 *"10327 in the GPU cache"*」= 用输入冒充输出。166 全盘 grep 该串**为空**。
3. **证据必须归档在它被引用的那一轮。**实例：W12 `k8v4` 那次没落 `stderr`，
   结论只能从「实测对照」降级为「源码推演 + int8 旁证」。**「跑过」不等于「有证据」。**
4. **改结论后必须全库 grep 同一断言。**实例：「四臂」在 W750 §1 改了、§2 没改，自相矛盾。
5. **`--kv` 的字面量 != `kv_mode`。**后者从**运行期 pool 布局**推得（`k8v4` => 3，`int8` => 1）。
   凡遇「某开关要求某模式」，**必须去读那个模式的定义处**，不能用命令行值直觉替代。
6. **`static thread_local` 一次性 banner 是「单向证据」**---- 可**证伪**，不能单凭它**证真**。
7. **`--max-new` 决定 `--dump-routing` 记录数的「量级」。**`--max-new 1` => 48 条；
   1024 => 3,838 positions => 184,224 条（**不是**1024x48）。`bench_eviction` 的 `lookups` 是
   **(layer,expert) 对数**（= 记录数 x k=10），不是记录数。
8. **native IQ pack 的 generate 路径强制三前置**：`--native SHARD1` + `--spec T(>=2)` + `--prefill CHUNK`，
   外加 `--ple-gguf <shard2>`（否则 Layer 1 的 PLE 静默跳过，改动一切下游数字）。
9. **容器挂载只有 `/data` 与 `/models:ro`**=> 脚本必须放 `/data` 下；查容器内文件走 `docker exec`。
10. **V12 `P55`/`P56` 的靶在 `k8v4` 下不可达，别去跑空跑的四臂**（W774 已踩过一次）。
11. **字节台账系统不可靠**：本会话三次报错字节/md5。**发车前/收车后各实读一次并当场落账。**
12. **审计必须独立上下文 + 只认原始证据**：本次 4 条 P0/P1 全部回原始证据复核后才落盘。
13. **落盘窗口**：`MEMORY.md` 有 3,000 字符注入窗，超窗内容会静默截断（现 4,212 B，见 §7 坑 7）。
14. **「禁用码位」规则写着但从未全库执行**：实测 1,731 个 md 里 488 个含禁用码位（共 11,089 处）。
    => **别以为体检会绿**；新产出必须写时就守（写 `->` / `=>` / `x` / `(1)`，不写箭头 / 破折号 / 乘号 / 带圈数字）。

---

## §9 物料地图

### 9.1 166 目录

| 路径 | 内容 |
|---|---|
| `/home/albus/strata166/` | 部署根（与本地 `deploy/` 同构） |
| `/home/albus/strata166/data/` | LIVE config · 日志 · 车脚本产物（`_w775_w13*` / `_w775_w12*`） |
| `/home/albus/strata166/data/_w775_w13.py` | W13 dump 车（5,034 B / `b2aa9fde...`，CLI 在 `cmd=[...]`） |
| `/home/albus/strata166/_w775_w13.sh` | W13 驱动器（2,645 B / `3994d946...`） |
| `/home/albus/strata166/data/_w775_w12.py` | W12 banner 探针（3,843 B / `5b81f46e...`） |
| `/home/albus/strata166/_w775_w12.sh` | W12 驱动器（2,538 B / `43be7059...`，含 `ARM` + `KV` 两参数） |
| `/models/huihui-ai/.../unsloth-UD-IQ4_XS/` | 模型 3 分片（shard2 = PLE 表所在） |

### 9.2 本机

| 路径 | 内容 |
|---|---|
| `deploy/params/` | register + gen_config + verify_config + 证据 |
| `deploy/tmp/` | **探针与车产物归档**（`w13_n1024/` 等）；**注意本机 W12 副本已落后 166 版本**|
| `deploy/W750_MASTER_PLAN.md` | **唯一合并待办表**（§0.0 现时点执行版） |
| `deploy/W775_HANDOVER.md` | **本件**|
| `.workbuddy/memory/` | MEMORY.md（长期，超窗）/ MEMORY_DETAIL.md / 逐日日志 |

### 9.3 技能（本项目相关）

改参数 / 发车 / 审计 / 记忆压缩 / 账本 ---- 各自有技能，**动手前先加载**。
本波用到的：`routeb-audit`（对抗性审计）· `routek-session-handover`（本交接）。

---

## §10 交接自身做了什么（本件也要可审计）

### 动作清单

1. **审计（第 2 步）**：派 `Explore` 只读子 agent（`routeb-audit` 技能）对本轮全部产出做对抗性复核，
   **本机再 4 条 P0/P1 逐条回原始证据复核**=> 结果落 `deploy/W775_AUDIT_delta.md`。
2. **修正（第 3 步落盘）**：2 个 P0 + 5 个 P1 全部修正，落 6 个文件（见 §10.2）。
3. **交接（第 4 步）**：本件 + `SESSION_KICKOFF.md` 刷新。

### 10.2 本轮修正清单（现算）

| 文件 | 修正内容 | 复核命令 |
|---|---|---|
| W775delta_W13_RESULT.md | 2048 档 pp 65.7->65.6；四结论加「命中率口径」；`10327` 撤「逐字」引用；`_w775_w13.sh` md5 更正；CLI 出处改 `_w775_w13.py` | `grep -c '10327 in the GPU cache'` 应为 2（均在更正注内） |
| W775delta_W12_BANNER.md | 「双证」改「源码主证 + int8 旁证」；撤 k8v4 出行；`kv_mode` 改四分支原文；脚本字节更正 | `grep -c 'active=0'` 应只出现在「无产物」注内 |
| PARAM_REGISTER.tsv | P55/P56 `value` 改「在 k8v4 下不可达」+ verdict 加【W775delta 修正 W774】；626 引用改四分支 | 75 行 / 11 列 / 状态计数不变 |
| W750_MASTER_PLAN.md | §2 #14/#15 同步（#15「四臂」-> 「D 臂为主，P55·P56 臂作废」）；§1 P1'' / §8 指针 | `grep -c '改为四臂'` 应为 0 |
| W713_PLAN.md | §6.4 #9/#10 同步口径 + k8v4 无产物标注 | -- |
| .workbuddy/memory/2026-10-11.md | 追加审计段（含两 P0 教训） | 见 §2.1 md5 |

### 10.3 完成的核查

- **核查 1 账本两边一致性**：本项目**无 routeK 式六账本**；权威件在本机 `deploy/`，
  166 侧只有**部署件副本**（`params/` 两机同步）。本波**未推送 deploy 交付件到 166**（无此要求）。
  => 判定：**不适用 routeK 的行级差集流程**；deploy 交付件以本机为准。
- **核查 2 现场复核**：见 §6（166 三方核对通过；本机无残留）。
- **核查 3 指纹快照**：见 §2.2（现读）。
- **核查 4 待裁定汇总**：见 §5。

### 10.4 数字来源

§2.1 / §2.2 / §2.4 / §6 全部本机或 166 现场现算（md5sum / wc -c / docker inspect / netstat / rocm-smi）。
**无一条来自记忆或上一版残留。**

### 10.5 本件的机器自审（`_hoa_w775.py`）

- 判据 **13 条**：字符体检（A1/A2/A3/A4）· 结构 12 节（B1/B2）· §2.1 表逐件回原始文件核 md5+字节（C3）·
  register 计数现算（D1/D2）· 引用件存在性（E1）· **内容判据 H11/H12/H13**· 自指豁免（G1）。
- **首轮 `BAD = 4`**：A1（`U+2605` x13 + `U+274C` x1）· A2（`U+00D7` x7 + `U+2014` x15 + `U+21D2` x10 + `U+2260`）
  · A3（emoji 1）· C1。
  - **A1/A2/A3 是文件本身错**（我写交接件时用了 ``/`x`/`--`/`=>`/`!=`，违反 BAN 清单）=> 已全部换成 ASCII 等价。
  - **C1 是判据错（假红）**：我的路径正则 `[\w./]+\.md` 在 `.workbuddy/memory/2026-10-11.md` 上被 `-` 截断，
    捕成 `11.md` => 报「表内件不存在」。**修法：正则加 `-`**（同技能 §4.2「取证命令与判据语义不匹配」形态）。
- **末轮 `BAD = 0`**（PASS=13）。该次运行发生在**最后一次改动之后**（先刷 §2.1 表 7 件现值，再修 §10.4/§10.5 交界伪影，然后重跑）。
- **自审器含内容判据**（H11 全称肯定须带依据 · H12 md5 可现算或表域内 · H13 已证伪旧值仅在回溯语境），
  => 满足技能 §4.3「`BAD = 0` 不得只是格式绿」。
- 已知边界：本自审器**不含「下游可解析性」判据**，也不检「结论是否被回源证伪」----
  那部分由 `deploy/W775_AUDIT_delta.md` 的独立子 agent 承担。

---

## §11 一句话交接（2026-10-11 05:3x 刷新）

**项目健康度**：**良好**。生产 `strata166-407` 0.1.42 正常运行（HTTP 200 / verify 26-0）、零残留、回滚位齐。
W775delta 双线收车（W13 矩阵 + W12 banner），**经独立审计发现 2 P0 / 5 P1 并全部修正**。

**下一步（按序）**：
1. **W12 D 臂**（P59/P60 x decode `ms/step` x 5 runs，生产同构）---- 唯一靶仍成立的新项。
2. **W12 k8v4 补产物**（消掉审计 P0-3）。
3. **W13 读上游**有无淘汰策略实现（决定是否提 feature）。
4. **[X] 先别动**：`P55`/`P56` 在 `k8v4` 下不可达，别再发四臂空跑车。
5. **`MEMORY.md` 超窗（4,212 B > 3,000）**，开工应先走技能压回窗内。
