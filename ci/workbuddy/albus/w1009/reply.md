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
| 8 | 本轮改动 | 生产零改动、零重启；disk = build = running = `eea5ea37…` 三方一致 |

**二、主线** gfx906/mi50 @ c409936f · tag `mi50-0.2.10-r32-17-gc409936f` · 落后 0 / 领先 0 · 上游 `ffa80d73` · 工作树脏 0 行。
**三、本次落生产** 改动 0；重启 0 次；停机 0；代码面 1 提交 `c409936f`（两轴数据 + 门，只读）。
**四、进度** 243 条 / 已结 163 / **67.1%**；队列 R95（P309）→ R98 → R94 → R91 → R89 → R46。

---

## 一、上一轮我把话说大了，这轮收回来

W1008 只用一条轴（每专家行数）就宣布「90% 在核外」。**漏了第二条轴：每次 launch 几个专家**。补测（`GROUP_SWEEP.tsv`，Q4_K gu，canonical，reps=20，每行成本）：

| 组大小 | 16 | 8 | 2 |
|---|---|---|---|
| ms/row @411 列 | 0.000434 | 0.000448（×1.03） | 0.000552（**×1.27**） |

两条轴相乘 **1.06 × 1.27 = 1.34**，实测 1.57 ⇒ **剩下 40% 未被解释，不是 90%**。而 40%×0.57 ≈ **110 ms**，正好等于 `host grouping` 的 84 ms（只在 2K 出现）+ `wait copy` 的 30 ms —— **两个已经单列的相位，没有神秘开销**。

## 二、六长度曲线否掉了一个模型

2K/4K/6K/8K/12K/16K 各 n=2 冷 prompt，gu 每 1k token：393.9 → 376.0 → 323.1 → 291.9 → 264.3 → **249.4**。

- 若 gu 含「每 chunk 固定成本」，用最长三点拟合外推到 2K 应当**偏高**；实际预测 1141 ms、实测 820 ms（**−28%**，R²=1.0000）⇒ **固定项模型被否，它是平滑效率曲线**。
- 方法自证：同法作用在 `gdn`（误差 2%）、`router+shared`（3%）上，说明不是方法偏。
- 相反 `dequant` 是**真固定量**：斜率 r²=0.009、截距 527 ms，≥8K 恒约 520 ms，2K 只有 165（专家并集小）。

## 三、门的更新

`kernel_curve.py --check` 现在校**两条轴 + 乘积**（1.06 / 1.27 / 1.34），任一漂移即 FAIL；本机与 166 都跑通。`P309`（两个事件的 busy/phase）仍要做，但目标从「找 270 ms」改成「确认那 110 ms 的归属」。

## 四、边界

- 组大小轴只有 Q4_K gu 一种类型、reps=20；`n=2` 是极端下端，生产 40 个专家一层时更像 16/16/8，实际系数小于 1.27。
- 六长度每档 n=2（相位差在 1–3% 内，够判单调性，不够判 2×CV 级效应）；每档 4 个重复留给需要下结论的那次 A/B。
