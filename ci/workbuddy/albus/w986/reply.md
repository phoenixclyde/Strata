## 一、生产容器（8 字段）

| # | 项 | 值 |
|---|---|---|
| 1 | 容器 / 镜像 | `4f387a12e84b` / `strata-gfx906:0.2.10-101`（image `5267df6dbdeb`） |
| 2 | 运行中引擎 | `eea5ea3749ad54b124330386605a18bc`，44,908,992 B（strata 0.1.56，v0.9.0 基线） |
| 3 | **config** | md5 `7a1cab853ff102c9d11ec9e662e83fe9`（env 删一项后的新指纹）；exe=`/data/bin/strata-0.1.56-090`；**args 35**；**env 8** |
| 3a | args 明细 | `--pack` `--native` `--expert-profile` `--expert-cache auto` `--pcie-frac 0.20` `--spec 4` `--spec-min-p 0.70` `--mtp` `--max-context 262144` `--kv k8v4` `--prefill auto:16384` `--prompt-cache-every 8192` `--expert-profile-save` `--conversation-cache-mib 4096` `--vision` `--mtp-window 8192` `--vram-reserve-mib 832` `--ple-io mmap` |
| 3b | env 明细 | `HSA_OVERRIDE_GFX_VERSION` `STRATA_PREFILL_CPU_SHARE` `STRATA_PREFILL_CPU_SHARE_MAX` `STRATA_ROCBLAS_TUNING` `STRATA_GFX906_TUNED` `STRATA_CKPT_MOVE_PARK` `STRATA_DECODE_TIMING` `STRATA_SPEC_DEPTH`（**`STRATA_RESIDENT_HEADROOM_GIB` 已删**） |
| 4 | 健康 | `/health` status=ok、`loaded:true`、**restarts=0**、StartedAt `2026-11-04T18:54:04Z` |
| 5 | 资源隔离 | `ulimit -l = unlimited`；引擎 `VmLck: 0 kB` |
| 6 | 显存布局 | `expert cache 7463 slots / 21.79 GiB`、`borrows 2606 (7.62 GiB)`、`882 MiB of VRAM free` |
| 7 | 回滚件 | 引擎 `strata-0.1.56-080`；`cp /data/strata-huihui-ud-iq4_xs.json.bak_w976 /data/strata-huihui-ud-iq4_xs.json` 后 `docker restart strata166-407` |
| 8 | 本轮改动 | 删 1 个死参（env 9→8）；账本 8 处；disk = build = running 三方一致 |

## 二、主线

`gfx906/mi50 @ 304bd3be` · tag `mi50-0.2.10-r32` · HEAD `2a74afbd` · 跟踪 `origin/gfx906/mi50` · **落后 0 / 领先 13** · 上游 `ffa80d73` · 工作树**脏 0 行**。

## 三、本次落生产

改动 **1 项**（删惰性 env），**重启 2 次**（A 臂 + B 臂回退），各 ≈45 s，**停机合计 ≈1.5 分钟**；回滚件同上。B 臂（pcie auto）由门自动回退，生产 pcie-frac 仍 0.20。

## 四、进度 + 队列

**180 条 / 已结 106 / 58.9%**；主线 **152 / 106**；死块池 **0/28**。
队列：**R88 → R93 → R89 → P239 → P244 → P48 → P33 → R91 → R86 → R87**。

---

## 五、全面审计（六轴）：2 个 P0、7 个 P1、6 个 P2，已整改 10 项

你说得对，上一轮是**应答式**审计。本件按六轴重做，脚本 `albus/w986/audit_full.py` + 逐条读原文，全部落在 `deploy/AUDIT25_W952_W985.md`。

| 轴 | 覆盖 | 发现 |
|---|---|---|
| **A 生产面** | 35 args + 9 env | 1 死参（已删）、1 无收益且阻挡候选（已测结案）、1 无使用证据（`--vision`，待你一句话）、1 未登记观测开关（已补册） |
| **B 账本面** | 180 条 | R88 正文与证据冲突（已改靶）；今日两条负面未入账（已补）；R84 标 INFLIGHT 但自 W951 无更新；P2 标 BLOCKED 无解除条件 |
| **C 参数册面** | 262 条 | P10 册值 `auto` vs 生产 `auto:16384`（已改）；P107 册值 rocBLAS **5.5** vs 生产 **5.7.0**（已改）；**10 条 ADOPTED env 在生产 env 里根本不存在**——实为二进制默认开（日志打印 `STRATA_HC_Q8=1:` / `STRATA_ROUTE_TAIL_SKIP=7 is ON`），口径应记 default-on |
| **D 轮次面** | W952–W985（31 轮） | **15 轮动过生产但台账无对应行**（W963/967/968/971–976/978–983）；6 轮只有 0–1 件近乎空转 |
| **E 门自身** | gate/cfg_apply/bench/compare/report_lint | **P0×2**（见下），已修 |
| **F 文档面** | W9xx 报告 | W970 写"0.8.0 基线"，实为 master `feaf8000`（W974 已更正） |

**两个 P0（会产生错误结论，已修）**：

1. **基线与臂的重启状态不同**——`pcie-frac 0.35/0.10` 读出"+4.3~4.4% 退化"，但**空操作臂（同值重启）+5.70%**：退化的是重启。修：`--restart-baseline`。
2. **中性即 KEEP**——`0.10` 无显著差异却留在生产。修：三分判定 + `--force-keep`。

## 六、本轮实际整改（可复核）

| 项 | 结果 |
|---|---|
| 删 `STRATA_RESIDENT_HEADROOM_GIB` | P65 自述"惰性"，删除；n=10：decode 37.01 / TTFT 4.0533 对 37.37 / 4.0743 ⇒ 无变化（env 9→8） |
| `pcie_frac_auto` 解锁实验 | decode +1.53%（band 11.68%）、TTFT −0.23%（band 1.18%）⇒ 不显著，**自动回退**；P227 结案 |
| 账本 | P252/P253/P258/P259x 四行；R88 改靶；P65→CLOSED；P10/P107 值更正；P227→REJECTED；新增 P254/P255/P256/P257 |
| 门 | `--restart-baseline`、三分判定、`--force-keep`、`--unset-env/--unset-arg`（4 个提交） |

## 七、优化后的方案（`deploy/W986_PLAN_V3.md`）

**执行序按"收益/成本"排，不按 R 编号排**：

| 序 | 项 | 预期 | 成本 |
|---|---|---|---|
| 1 | R88-1 首块分阶段计时 | 无收益，是后续判断的前提 | 低 |
| 2 | **R93 chunk 重标**（8K 凹陷 715 vs 16K 780） | 8K 段 +3~8% | 低 |
| 3 | R89 QSA 是否已 gather-only | 已则 DONE_NEG，否则 +10% 级 | 低 |
| 4 | **R88-2 首块预取原型** | TTFT 4.05 → **≤3.0 s** | 中 |
| 5–9 | P239 / P244 / P48 / P33 / R91 | 未量化 | 低→高 |

**明确划掉（有数据）**：数据分层再调（W975 −60%）、`--pcie-frac` 数值（W983 n=10 无差别）、pcie auto（W986 不显著）、`--pool-tasks`（+3.87%）、会话/检查点缓存（W979 无差别）、`--mmap-experts`（−19%/−60%）。

## 八、下一步

1. **R93 先行**：8K 凹陷是纯配置问题，`cfg_apply` 三档（8192/16384/32768）各 n=10；
2. 同时做 **R88-1 计时**（只加输出，不改行为）；
3. 账本债：39 个未审 R + R84 陈旧状态 + P2 解除条件，按 AUDIT25 §6 逐条清；
4. 需要你一句话的：**`--vision` 到底用不用**（不用则删，省 VRAM 与一条代码路径）。
