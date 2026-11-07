## 一、生产容器（8 字段）

| # | 项 | 值 |
|---|---|---|
| 1 | 容器 / 镜像 | `4f387a12e84b` / `strata-gfx906:0.2.10-101`（image `5267df6dbdeb`） |
| 2 | 运行中引擎 | `eea5ea3749ad54b124330386605a18bc`，44,908,992 B（strata 0.1.56，v0.9.0 基线） |
| 3 | **config** | md5 `49bf0c812fe5e53db4a00b5be97e3a13`；exe=`/data/bin/strata-0.1.56-090`；**args 35**；**env 9** |
| 3a | args 明细 | `--pack` `--native` `--expert-profile` `--expert-cache auto` `--pcie-frac 0.20` `--spec 4` `--spec-min-p 0.70` `--mtp` `--max-context 262144` `--kv k8v4` `--prefill auto:16384` `--prompt-cache-every 8192` `--expert-profile-save` `--conversation-cache-mib 4096` `--vision` `--mtp-window 8192` `--vram-reserve-mib 832` `--ple-io mmap` |
| 3b | env 明细 | `HSA_OVERRIDE_GFX_VERSION` `STRATA_PREFILL_CPU_SHARE` `STRATA_PREFILL_CPU_SHARE_MAX` `STRATA_RESIDENT_HEADROOM_GIB=0.5` `STRATA_ROCBLAS_TUNING` `STRATA_GFX906_TUNED` `STRATA_CKPT_MOVE_PARK` `STRATA_DECODE_TIMING` `STRATA_SPEC_DEPTH` |
| 4 | 健康 | `/health` status=ok、`loaded:true`、**restarts=0**、StartedAt `2026-11-04T17:59:16Z` |
| 5 | 资源隔离 | `ulimit -l = unlimited`；引擎 `VmLck: 0 kB`（无 mlock、无 pin） |
| 6 | 显存布局 | `expert cache 7463 slots / 21.79 GiB`、`borrows 2606 (7.62 GiB)`、`882 MiB of VRAM free` |
| 7 | 回滚件 | 引擎 `strata-0.1.56-080`；`cp /data/strata-huihui-ud-iq4_xs.json.bak_w976 /data/strata-huihui-ud-iq4_xs.json` 后 `docker restart strata166-407`（另有 `.bak_w978` / `.bak_w979b`） |
| 8 | 本轮改动 | **生产配置零改动**；改的是门：`ci/gate.py`（+98 行配置校验）、`ci/cfg_apply.py`、`ci/hooks/pre-commit`；disk = build = running 三方一致 |

## 二、主线

`gfx906/mi50 @ 304bd3be` · tag `mi50-0.2.10-r32` · HEAD `3c663620` · 跟踪 `origin/gfx906/mi50` · **落后 0 / 领先 10** · 上游 `ffa80d73` · 工作树**脏 0 行**。

## 三、本次落生产

改动 **0 处（配置面）**；代码面 3 个提交（门）。重启 **2 次**（P4-d1 实验 + 自动回滚），各 ≈45 s，**停机合计 ≈1.5 分钟**。回滚由门自动完成，人工命令同上。

## 四、进度 + 队列

**176 条 / 已结 102 / 58.0%**；主线 **148 / 102**；死块池 **0/28**。
队列：**R88 → R86 → R87 → R46 → R91 → R93 → R72 → R81 → R79/R80 → R63/R60/R64**。

---

## 五、门为什么没卡住：三条，全是"有工具没人调"

| 门 | 存在吗 | 为什么没拦 |
|---|---|---|
| `ci/strata-ci check`（18 项） | 在 | **没有调用者**——它不是 CI，是我手动跑；我改配置时直接 `json.dump` + `docker restart`，一次都没跑 |
| `ci/bench.py` + `ci/compare.py`（2×CV） | 在 | 我用临时 python 脚本测，**没有记录、没有 CV、没有 2×CV 判定** |
| `tools/report_lint.py`（12 字段） | 在 | 我这几轮**根本没跑**，所以"四项报告"缺了也没人拦 |

更具体地说，`gate.py` 当时只校验了 `exe` 存在、`/health`、一个 env 取值，**不看 `env` 的类型、不看 `args` 是否合法**——所以我那次把 `env` 写成 list，它能"崩"但不能"判"。

## 六、已经改成机制（不靠我记得）

| 环节 | 之前 | 现在 |
|---|---|---|
| 提交代码 | 无门 | `pre-commit` → `gate.py --source-only`，不过不许提交（已装，`ci/install-hooks.sh` 可重装） |
| 改配置 | 手改 JSON + restart | **`ci/cfg_apply.py` 是唯一入口**：候选 → gate → 备份 → 安装 → 重启 → 等 `loaded:true` → 测 decode/TTFT → 2×CV → 不过**自动回滚** |
| 报告 | 想跑才跑 | 每轮先 `report_lint.py`，本轮就是 lint 通过后才发的 |

**负向自测（证明门真的会拦）**：

| 注入的错误 | 结果 |
|---|---|
| `env` 由 dict 改成 list（复刻事故） | `FAIL config env is a dict — got list … dies before binding` |
| 重复 `--ple-io` + `--ple-io fast` + `--bogus` | 3 条 FAIL（重复 / 非法枚举 / 未知 flag） |
| 现役配置 | **23 项全过** |

## 七、门第一次实战：P4-d1 被判否

| 臂 | decode(tok/s) | TTFT 2K(s) |
|---|---:|---:|
| p4-base（现役） | **35.77**（CV 2.3%） | **3.948**（CV 0.4%） |
| p4d1 `--pool-tasks 6` | 32.85（CV 8.68%） | **4.1005** |
| 判定 | −8.17% < 带宽 17.36%（不显著） | **+3.87% > 带宽 0.80%** |

⇒ **`ROLLBACK`（自动执行，health 已确认 ok）**：`pool-tasks=6` 让 TTFT 变差 3.9%，**P4-d1 排除**。

这一步正是以前会漏的：单次采样时 4.10 vs 3.95 只差 0.15 s，我会当成噪声放过去；门用 CV 算出的带宽只有 0.8%，直接判否并回滚。

## 八、下一步（继续走门）

1. **P4-d2**：`--pcie-frac 0.35`，同样 `--baseline p4-base --n 5`，判据不变；
2. 若也否 ⇒ **R88 立项**，靶子按上一轮的证据改为"首块 CPU/GPU 串行"；
3. 顺带把 `report_lint` 接进提交前流程（我这边已按"先 lint 再发"执行）。
