**一、生产容器（8 字段）**

| # | 项 | 值 |
|---|---|---|
| 1 | 容器 / 镜像 | `4f387a12e84b` / `strata-gfx906:0.2.10-101`（image `5267df6dbdeb`） |
| 2 | 运行中引擎 | `eea5ea3749ad54b124330386605a18bc`，44,908,992 B |
| 3 | config | md5 `e62685e6ff21d9e2b60c1cd622fd5a67`；exe=`/data/bin/strata-0.1.56-090`；args 37；env 9 |
| 3a | args 明细 | `--pack /data/packs/ud-q4_k_xl --native … --expert-cache auto --pcie-frac 0.20 --spec 4 --spec-min-p 0.70 --mtp /data/mtp/rt --max-context 262144 --kv k8v4 --prefill auto:16384 --prompt-cache-every 8192 --conversation-cache-mib 4096 --vision --mtp-window 8192 --vram-reserve-mib 832 --ple-io mmap --pool-workers 10` |
| 3b | env 明细 | `HSA_OVERRIDE_GFX_VERSION` `STRATA_CKPT_MOVE_PARK` `STRATA_DECODE_TIMING` `STRATA_GFX906_TUNED` `STRATA_PREFILL_CPU_SHARE` `_MAX` `STRATA_PREFILL_TIMING` `STRATA_ROCBLAS_TUNING` `STRATA_SPEC_DEPTH` |
| 4 | 健康 | `/health` ok、`loaded:true`、restarts=0、StartedAt 2026-11-05T11:58:52Z |
| 5 | 资源隔离 | `ulimit -l` unlimited；`VmLck` 0 kB |
| 6 | 显存布局 | expert cache 7463 slots / 21.79 GiB、borrows 2606（7.62 GiB）、882 MiB of VRAM free |
| 7 | 回滚件 | `strata-0.1.56-080`；`cp /data/strata-huihui-ud-iq4_xs.json.bak_w976 /data/strata-huihui-ud-iq4_xs.json` + `docker restart strata166-407` |
| 8 | 本轮改动 | 生产零改动、零重启；disk = build = running = `eea5ea37…` 三方一致（只读 `WIDTH_SWEEP.tsv`） |

**二、主线** gfx906/mi50 @ 48565cdd · tag `mi50-0.2.10-r32-16-g48565cdd` · 落后 0 / 领先 0 · 上游 `ffa80d73` · 工作树脏 0 行。
**三、本次落生产** 改动 0；重启 0 次；停机 0；代码面 1 提交 `48565cdd`（`ci/prefill_phases/kernel_curve.py`，只读门）。
**四、进度** 240 条 / 已结 160 / **66.7%**；队列 R95（P309 实验）→ R98 → R94 → R91 → R89 → R46。

---

## 一、结论：这 1.57× 不在 GEMM 核里，占 90%

答案本来就在仓库里。`WIDTH_SWEEP.tsv` 是**同一个 kernel、同样 16 专家一组**、生产形状与类型的 canonical 路径 —— `MMQ_GROUP = 16`（`prefill.cpp:1401`），正好等于 bench 的 `n=16`。它只差没除以行数：

| rows/expert | gu Q4_K @[1280,2560] | dn Q5_1 @[2560,640] |
|---|---|---|
| 32 | 0.000579 ms/row（×1.41） | 0.000453（×1.79） |
| 128 | 0.000500（×1.22） | 0.000274（×1.08） |
| 320 | 0.000441（×1.075） | 0.000255（×1.01） |
| 512 | 0.000426（×1.04） | 0.000253（×1.00） |
| 1024 | 0.000410（×1.00） | 0.000253（×1.00） |

2K 每组均值约 **411** 列、16K 约 **1015** 列，插值：

- **gu：核内预测 1.06×，实测 1.57× ⇒ 90% 在核外**
- **dn：核内预测 1.01×，实测 1.52× ⇒ 99% 在核外**

## 二、这条结论改变了什么

R95 从 W990 起把账记在「小批 GEMM / tile 填不满」上，W992 又证明 J=64 是几何下限，于是这条线看起来堵死了。实际是**归错了地方**：tile 几何只值 5–7 个百分点，剩下的 50 个在**组循环里、核外**——`wait copy`（已单列 37 ms）、组内建表与派发、MMQ 尾块清零、组间事件。**这四个都不需要动 kernel**，也意味着 R86（权重 repack）对 2K 的帮助比原估计更小。

下一步（`P309`，判据已写死）：在 build-tab 分支树给组循环加两个事件（16 专家 launch 前后），2K 与 16K 各跑一次，看 `busy/phase`：
`< 0.80` ⇒ 主机派发饿着 GPU（解法：建表挪 issuer 线程、组批提交）；`≥ 0.95` ⇒ 核内另有开销，回查激活布局与 group strides。

## 三、门

新增 `ci/prefill_phases/kernel_curve.py --check`：从 `WIDTH_SWEEP.tsv` 重算每行成本与 2K/16K 比值，方案写 1.06/1.01 不符即 FAIL。已接进 `round_close.py` 的 `SCRIPT_HARD`（本机与 166 都跑通），并随 `48565cdd` 进仓（GitHub run #29 由这次提交触发）。

其余五道门本轮全绿：`report_lint` / `plan_lint` / `AUDIT_INDEX` / `PLAN_RETIRED` / `POINTER` + 六件权威件逐字节一致。

## 四、边界

- 只读，没跑新 bench。中途试过「单专家 vs 16 专家」的 per-call 开销，`n=1` 时 0.1–0.5 ms 的绝对量被计时噪声淹掉（128 行比 320 行还慢），**不可用，已弃**，结论不依赖它。
- 每组均值 411 / 1015 是估计（由 W991 的 p50=331/p90=742 与并集饱和推得），所以门里写成插值区间；`P309` 的实验会给准确值。
