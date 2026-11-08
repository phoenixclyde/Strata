# W1053 回执：AUDIT29 补审 W1032–W1052（21 轮）——1 P0 / 4 P1 / 6 P2，审计债 21→0

**一、生产容器（10 字段，本轮结束时）**

| # | 字段 | 值 |
|---|---|---|
| 1 | 容器 / 镜像 | `2d765942e041` · `strata-gfx906:0.2.11-101` · restarts=0 |
| 2 | 运行中引擎 | `strata-0.1.57-hc4b` · md5 `0533074826258d5f96c4b65bc0ad33df` · 43,679,864 B，未换件 |
| 3 | config | md5 `8d234fa38261abbee0328c80416d6835`（W1049 装机态原样）· `exe=/data/bin/strata-0.1.57-hc4b` · args 38 / env 13，未改 |
| 3a | args 明细 | 38 项逐字未动：`--pack` `--native` `--expert-profile` `--expert-cache auto` `--pcie-frac 0.20` `--spec 4` `--spec-min-p 0.70` `--mtp` `--max-context 262144` `--kv k8v4` `--prefill auto:16384` `--prompt-cache-every 8192` `--expert-profile-save` `--conversation-cache-mib 4096` `--vision` `--mtp-window 8192` `--vram-reserve-mib 832` `--ple-io mmap` `--pool-workers 10` `--kv-grow` |
| 3b | env 明细 | 13 项逐名未动：`HSA_OVERRIDE_GFX_VERSION` `STRATA_PREFILL_CPU_SHARE` `STRATA_PREFILL_CPU_SHARE_MAX` `STRATA_ROCBLAS_TUNING` `STRATA_GFX906_TUNED` `STRATA_CKPT_MOVE_PARK` `STRATA_DECODE_TIMING` `STRATA_SPEC_DEPTH` `STRATA_PREFILL_TIMING` `STRATA_GFX906_ATTN_DP4A=1` `STRATA_HC_DOWN_DP4A=1` `STRATA_HC_DOWN_DP4A_MAX_T=6` `STRATA_GFX906_ATTN_LDS_PAD=1` |
| 4 | 健康 | `/health` → `{"status": "ok", "max_context": 262144}` · restarts=0 · StartedAt `2026-11-08T05:14:12Z`（W1052 末次还原后未再动） |
| 5 | 资源隔离 | `ulimit -l` unlimited · `memlock=-1:-1` · `VmLck 0 kB` |
| 6 | 显存 | VRAM free 849,211,392 B（0.79 GiB）；expert cache 8301 槽 / 24.23 GiB；borrows 2609 槽 (7.62 GiB)（W1052 末值，本轮只读） |
| 7 | 回滚件 | `attn`（`3b758f88…`）+ `kvg`；备份 `tmp/w1052/cfg_pv_pre.bak`；rollback = `cp` 回备份 json 并冷重启（≈45 s） |
| 8 | 本轮改动 | **零落生产**：换件 0、config 改 0、**重启 0 次 / 停机 0 s**、装机 0、回滚 0；disk = build = running 三方一致 |
| 9 | ROCm | 打包 .info/version 10.1.0；HIP 7.16.26323；clang 24 · `--offload-arch=gfx906` |
| 10 | llama.cpp | b12180 = `bcb0152876e8f0b684ba70d3defcab6cdf35adb5` + `mmq*` @ `4c1004c49221b07c3b8108977e3d1991fc9f45cc` |

**二、主线** — `gfx906/mi50` @ e181bda5（`mi50-0.2.11-r33-14-2-ge181bda5`）；生产树 `pr/k10` @ `5fb89860c`，领先 0 / 落后 0 / 脏 0 行，上游本轮未重算。审计件 `deploy/AUDIT29_W1032_W1052.md`；新门 `tools/ci_runs_lint.py`（自测 6/6）、`tools/ledger_lint.py` 重写（自测 8/8）；覆盖基线 `deploy/TABLE_SHAPE_BASELINE.tsv`。

**三、本次落生产** — **零**：装机 0 / **0 分钟停机**；**重启 0 次 / 停机 0 s**（本轮全部是只读取证与本机文件／工具改动，一次容器操作都没有）。窗口取证累计 0；回滚 0。

**四、进度** — **520 条 / 已结 431 / 82.9%**（分母变化来自本轮新增 12 条 `P561`–`P572`；已结 +12 = 新增 12，旧账净变化 0）。**审计债 21 → 0**（`audit_scope: PASS (debt 1/8)`，那 1 是 W1053 自己）。队列：**R116（PV dot4 离线预算）→ R74（W4A4 离线精度门）→ R91（dot8 接入）→ R85（prefill 台阶，手段序 R46 > R64 > R60）→ R89 → R95 → R86 → R101**（详见 `W832 §0.1`）。

## 1 审计范围与结论（21/21 点名）

`audit_scope` 直接给边界：`universe=53 covered_max=W1031 tail_debt=21`。本轮按它逐轮点名 W1032–W1052，
四轴取证：**账本结构** / **报告↔账本↔产物** / **A 级复跑** / **在线与在产复核**。11 条发现全部整改或登记：

| id | 级别 | 一句话 |
|---|---|---|
| A29-1 | **P0** | 方案 §0.1「唯一队列」与账本冲突且结构损坏（R110/R112 已判否仍置顶、R106/R107 已结仍写作待办、嵌套粗体断裂、W1037 残段、R103 重复）——整格重写 |
| A29-2 | P1 | `CI_RUNS` 生产 exe 行 run id 少一位（404），D7 只读状态列 ⇒ 证据可空转——改真值 + 新增 `ci_runs_lint` |
| A29-3 | P1 | 5 条「已结仍挂 OPEN」（R104/P457/P492/P511/P555）——逐条结案 |
| A29-4 | P1 | 4 条 OPEN 却 `done=1` 虚增已结（+范围外 3 条同形清扫）——纠正并补解除条件 |
| A29-5 | P1 | `ledger_lint` 209 误报、无退出码、仅 SOFT——重写并进 HARD |
| A29-6 | P2 | 46 行方案表格损坏——建基线、修好一处真粘连（46→35） |
| A29-7 | P2 | 32 份 `reply.md.bak*` 破坏「报告唯一副本」——收进 `_bak/` |
| A29-8 | P2 | `R107` 行判据写 9 轮口径、证据轮次清单损坏（W1043 重复三次、缺 W1046–W1052）——修复 |
| A29-9 | P2 | 5 条判否 R 行用 `DONE` 记，与 R99/R100/R102 的 `DONE_NEG` 不一致——4 条改正 |
| A29-10 | P2 | 跨分支引用歧义（`ci/lcpp_picks` 只在 `gfx906/lcpp-picks`；`tools/gfx906_dot48_selfcheck.cu` 实为 `albus/w1042/...`）——立命名空间规则 |
| A29-11 | P2 | trap 缺陷复发（W1044 `P515` → W1051 `g2d`）——登记「教训未机械化」 |

## 2 三道门为什么没拦住（本轮最值钱的部分）

### 2.1 `CI_RUNS` + D7：证据行可以是 404（A29-2）

`03509d1b…`（生产 `hc4b` 的构建 sha）那一行记的是 `4238161670`——**10 位**，真值是 `42378161670`。
D7 的实现只读第 4 列：`if status == "success": return True`。于是「表里写了 success」冒充「run 真的 success」。
**这是 W1048 立 D7 时埋下的**：门核的是表，不是事实。新增 `tools/ci_runs_lint.py`：

- 离线：run id 必须 11 位（10 位必是掉字）、状态枚举、`(key,ref)` 不重复、key 是 hex 或配方表里的 exe；
- `--live`：逐条查 GitHub，**run 存在 + conclusion 等于记录值 + head_sha 前缀等于记录的 sha**；
- 自测 6/6（含「run 404 必须 FAIL」）；改真值后 24 条 run 全部复核通过。

### 2.2 `ledger_lint`：209 条问题、0 条能拦（A29-5）

```
$ python tools/ledger_lint.py       # 修前
ledger rows 476 | problems 209
  PROGRESS row 317 P407  : 11 columns      <- 误报：W1035 起就该 11 列
$ echo $?                                  # <- 没有 sys.exit，永远 0
```
`round_close` 又把它放在 **SOFT**。⇒ AUDIT24 立的「表格 cell 数必须对齐」从建立那天起就没生效过，
AUDIT29 自己写报告时也被它抓出 4 行——**门是好的，只是从来没接上电**。现在：10/11 列、`KW:` 起头、
表格**基线制**（超基线才 FAIL）、rc=1、自测 8/8，并从 SOFT 移入 **HARD**。

### 2.3 队列与账本各说一套（A29-1）

方案 §0.1 自称唯一排期源，账本说 R110/R112 判否、R106/R107 已结，队列却把 R110/R112 置顶、把
R106/R107 写成「新立待办」。`plan_lint` 只查「R 号有没有账」，不查「排期与状态是否一致」，所以一直 PASS。
重写后队列分五段（在开 / prefill 台阶 / 第三 / 治理 / 存量）+ 已结单列，第一项是 **R116**。

## 3 A 级复跑（数字必须复现，不接受「报告这么写」）

| 轮 | 复跑对象 | 结果 |
|---|---|---|
| W1049 | `phase_b_full.txt` 的 8K `qsa attn`（n=3） | floor **1261.7**（cv 0.07%）、dp4a **1119.0**、combo **1103.7**（cv 0.09%）⇒ −1.37%；`k_ilp` 1761.7（+39.6%）——与报告逐位一致 |
| W1051 | `decode_g2c.txt` 的 8 对配对 | 逐对 `+4.88/−0.94/−2.37/+3.21/+3.80/−4.60/+2.06/+0.56` ⇒ 均值 **+0.82%**、population sd 3.07% ⇒ **2×SE 2.17%** |
| W1052 | `pv.dump`（22 记录 / 12,804 P / 67,584 输出） | **rel-rms 4.5951%**（报告 4.60%）；P 中位 8.037e-3、90 分位 0.166、峰值 1.0 |

**自曝一次取样面错误**：复跑 W1051 时第一版脚本用 `\(([0-9.]+) tok/s\)` 抓到了同一行的 **prompt 速度**，
得出「+0.22% ≠ +0.82%」的假分歧；改成 `600 generated in \d+ ms \(…\)` 后逐对复现。
审计工具本身也要有取样面校验——这条写进审计件。

## 4 在产与外部复核

- **生产**：容器 running / restarts 0、引擎 `hc4b` md5 `05330748…`（disk=build=running）、config `8d234fa3`（args 38 / env 13）、`/health` ok。
- **md5 链连续**：`53ac61e0`（W1032–36）→ `5e9b81e2`（W1037–39）→ `ee69ebc2`（W1040–43）→ `3dde8801`（W1044–46）→ `9e2df560`（W1047–48）→ `8d234fa3`（W1049–52），21 轮之间没有「说不清是谁改的」config。
- **CI**：`CI_RUNS` 27 行（24 条非豁免）逐条查 API，**结论与 head_sha 全对**；唯一不合就是 A29-2 那一行（已修）。
- **R105 的 93 处**：166 上 `grep -rn STRATA_HIP_GFX906 src include third_party | wc -l` = **93**，与 `P559` 一致。
- **runner**：`actions.runner.phoenixclyde-Strata.strata166-gfx906` = `active`；`gpu-gate.yml` 只有 `workflow_dispatch` + `push: ci/**`，**无 `pull_request`**。

## 5 边界（不冒充完成）

- **35 行历史表格损坏未改写**（只登记 + 基线；原本 46，本轮修好 11 行）。机械化改写「哪些竖线是内容」要语义判断，改错会再劈一次。
- **历史报告的跨分支引用不追改**（改历史报告=伪造当时证据），只对今后报告执行命名空间规则。
- **`P424`/`P455`/`P481` 仍 OPEN**（已补可判定的解除条件）；`R116`/`R74`/`R91`/`R85` 按 §0.1 队列推进。
- **A29-11 只登记未机械化**：窗口脚本模板的 restore 断言留待下一步（本轮不动生产、不动在跑的流程）。
- **A 级复跑只覆盖 W1049/W1051/W1052**（数据件在本机）；W1032–W1048 核的是账本、产物、报告数字与 md5 链，没有重跑它们的 GPU 窗口。

落点可复核：审计件 `deploy/AUDIT29_W1032_W1052.md:1`；门 `tools/ci_runs_lint.py:1`、`tools/ledger_lint.py:1`；基线 `deploy/TABLE_SHAPE_BASELINE.tsv:1`；账本行 `deploy/PROGRESS.tsv`（`P561`–`P572`）；方案回写 `deploy/W832_OPT_PLAN_V2.md` 的 W1053 段；收工门挂点 `albus/w1002/round_close.py:24`。
