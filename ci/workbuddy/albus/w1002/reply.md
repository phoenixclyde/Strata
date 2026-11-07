## 一、生产容器（8 字段）

| # | 项 | 值 |
|---|---|---|
| 1 | 容器 / 镜像 | `4f387a12e84b` / `strata-gfx906:0.2.10-101`（image `5267df6dbdeb`） |
| 2 | 运行中引擎 | `eea5ea3749ad54b124330386605a18bc`，44,908,992 B（strata 0.1.56，v0.9.0） |
| 3 | **config** | md5 `e62685e6ff21d9e2b60c1cd622fd5a67`；exe=`/data/bin/strata-0.1.56-090`；**args 37**；**env 9** |
| 3a | args 明细 | `--pack` `--native` `--expert-profile` `--expert-cache auto` `--pcie-frac 0.20` `--spec 4` `--spec-min-p 0.70` `--mtp` `--max-context 262144` `--kv k8v4` `--prefill auto:16384` `--prompt-cache-every 8192` `--expert-profile-save` `--conversation-cache-mib 4096` `--vision` `--mtp-window 8192` `--vram-reserve-mib 832` `--ple-io mmap` `--pool-workers 10` |
| 3b | env 明细 | `HSA_OVERRIDE_GFX_VERSION` `STRATA_PREFILL_CPU_SHARE` `STRATA_PREFILL_CPU_SHARE_MAX` `STRATA_ROCBLAS_TUNING` `STRATA_GFX906_TUNED` `STRATA_CKPT_MOVE_PARK` `STRATA_DECODE_TIMING` `STRATA_SPEC_DEPTH` `STRATA_PREFILL_TIMING` |
| 4 | 健康 | `/health` status=ok、`loaded:true`、max_context=262144、**restarts=0**、StartedAt `2026-11-05T11:58:52Z` |
| 5 | 资源隔离 | `ulimit -l = unlimited`；引擎 `VmLck: 0 kB` |
| 6 | 显存布局 | `expert cache 7463 slots / 21.79 GiB`、`borrows 2606 (7.62 GiB)`、`882 MiB of VRAM free` |
| 7 | 回滚件 | 引擎 `strata-0.1.56-080`；`cp /data/strata-huihui-ud-iq4_xs.json.bak_w976 /data/strata-huihui-ud-iq4_xs.json` 后 `docker restart strata166-407` |
| 8 | 本轮改动 | **生产零改动、零重启**；只改仓库 CI、台账与文档；disk = build = running = `eea5ea37…` **三方一致** |

## 二、主线

`gfx906/mi50 @ ab68576c` · tag `mi50-0.2.10-r32` · HEAD `ab68576c` · 跟踪 `origin/gfx906/mi50` · **落后 0 / 领先 0** · 上游 `ffa80d73` · 工作树**脏 0 行** · 远端一致（GitHub API：`remote HEAD = ab68576caaf6`）。

## 三、本次落生产

配置改动 **0**；**重启 0 次**；停机 **0**；回滚件同第一项第 7 条（未使用）。代码面：1 个提交 `ab68576c`（14 文件 / +824 行，全是 CI 与实验证据），连同积压的 16 个提交共 **17 个**推送到 `origin/gfx906/mi50`（`5f73cd15..ab68576c`）。生产二进制与 config 指纹本轮前后相同。

## 四、进度 + 队列

**209 条 / 已结 131 / 62.7%**；主线 **181 / 131**；死块池 **0/28**。
队列：**R97 → R96 → R86 → R91 → R95 → R94 → R89 → R46 → R49**（唯一权威在 `W832_OPT_PLAN_V2.md §6.5`）。

---

## 五、三问，直接答

| 问 | 答 |
|---|---|
| 完整移植了吗 | **没有**。只做到独立 bench 的公平 A/B（W1001），`src/`、`include/`、`CMakeLists.txt` 零改动。机器可读状态：`ci/repack_ab/PORT_STATUS.md` 明确 `PRODUCTION_PORT = NOT_DONE`，六条通道 C1/C2/C5/C6 全 NOT_STARTED |
| 四项报告呢 | W994–W999 的报告件有并过了 lint，但 **W996 / W1000 / W1001 三条回复没有四件套章节**，违反纪律⑳（每条回复都要以它开头）。本轮补齐，并把「先 lint 再发」变成收尾门 |
| CI/CD 呢 | **有工具、没跑**：16 个提交未推、`strata-ci check` 一次没跑、`report_lint` 没接进任何 hook。本轮推 17 提交，GitHub **Downstream gate run #25 completed / success @ `ab68576c`**，`strata-ci check` **18/0** |

## 六、追问「门呢」：W980 的承诺没兑现

W980 我写「改成机制、不靠我记得」，**实际只装了 `pre-commit → gate.py --source-only`**（源码门）。
报告、实验产物、推送三处没有调用者 ⇒ 照样漏。**有工具 + 没人调 ≠ 门。**

本轮补的是**调用者**：

| 触发 | 门 | 拦什么 |
|---|---|---|
| `git commit` | pre-commit → `gate.py` + `round_gate.py --ci` | 配置面缺陷；证据缺失/被改；lint 不再拦坏报告 |
| `git push` | pre-push → fork 策略 + `round_gate.py --ci` | 推到上游；把证据不全的状态发出去 |
| GitHub push | `downstream-gate.yml` → `verify.py` + `round_gate.py --ci` | 同上，在干净 runner 独立复核 |
| 166 收尾 | `round_gate.py --status` | 未推提交、脏工作树、hook 未装 |
| 本机收尾 | `albus/w1002/round_close.py --report` | `report_lint` / `plan_lint` 不过 |

**负向自测 5/5**（`albus/w1002/negative_test.py`）：伪造 ratio、清空 PORT_STATUS、删 `mmq::quantize` 标记、摘掉 workflow 里的 verify 调用、把 `report_lint` 换成恒 exit 0 —— 五种都让门 FAIL、恢复后 PASS。
门第一次正向运行还抓到真缺陷：Windows 上传的 `RESULTS.tsv` 带 **UTF-8 BOM**，首行注释被当成第 5 条数据；`run.sh` 的 BOM 会让 shebang 失效。已去 BOM、校验器改 `utf-8-sig`。

## 七、追问「还有个 lint」：四个都查了

| lint | 之前 | 本轮 |
|---|---|---|
| `report_lint` | 本机孤立、无调用者 | 入仓 `ci/report_lint.py`，四处调用 + 正反自测 |
| `plan_lint` | **rc=1 FAIL**，4 份 PLAN 未登记（含活方案 `W986_PLAN_V3.md`），没人看见 | 按纪律整改而非绕过：V3.9 队列回写 `W832 §6.5`，W986 标 SUPERSEDED，四份按角色登记 ⇒ **PASS** |
| `ledger_lint` | 59 problems，其中 **30 行台账只有 9 列** | 补齐第 10 列 `ref` ⇒ 29 problems |
| `param_pair_lint` | 15 处族内滞后 | 收尾门汇总，列为待办 |

剩余 29 项警告如实登记（W832 历史表格裸 `|`、短 note、族内滞后），**没有假装清完**。

## 八、外网核对（用于定门的设计，不是装饰）

- **GitHub Docs · workflow syntax**：`branches` 与 `paths` 必须同时满足才触发；只写 `branches` 不含 `tags` 时 tag push 不跑；push 用两点 diff、PR 用三点 diff ⇒ 本次 `ci/**` 改动**应当**触发，run #25 是实证。
- **GitHub Docs · required status checks**：强制力来自分支保护，不是 workflow 自带；我们单人单分支不开 PR ⇒ 等价物是 `pre-push` 本地拦，不引入 merge queue。
- **Continuous benchmarking 实践**（InferenceBench CI recipe 等）：性能回归门需 self-hosted GPU runner + 基线 envelope + tolerance，且**不宜挂每次提交**；还要防「门被降级成 warning」⇒ `verify.py` 特意检查 workflow 里调用仍在，`round_gate` 做正反自测。与 `CI_CD_POLICY.md §7` 一致：静态门上云，GPU bench 留 166 人在环。

## 九、交付件与下一步

新增/修改：`ci/repack_ab/`（7 件：README、RESULTS.tsv、PORT_STATUS.md、两份 `.cu`、run.sh、verify.py）、`ci/report_lint.py`、`ci/round_gate.py`、hooks ×2、`downstream-gate.yml`、`ci/README.md`；本机 `deploy/W1002_ENGINEERING_STATUS.md`、`deploy/CI_CD_RUNBOOK.md §10`、`deploy/W832_OPT_PLAN_V2.md §6.5`、`deploy/W986_PLAN_V3.md`（SUPERSEDED）、`tools/plan_lint.py`、`deploy/PROGRESS.tsv`（+3 行、修 30 行）、`albus/w1002/*`。

下一步不变：**R97-1 混合分派原型**（在 `ab_bench` 内按段拆两个 launch，出加权单内核收益）→ ≥5% 才进 `PORT_STATUS` 的 C1/C2 完整移植；R96 源码可行性与 R94 质量门并行。完整移植要动专家借槽上传路径，必须带逐位等价与回滚窗口，本轮不硬上。

（本件已过 `report_lint` 与 `round_close` 四个 lint；负向自测 5/5。）
