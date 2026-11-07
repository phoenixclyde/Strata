**一、生产容器（8 字段）**

| # | 项 | 值 |
|---|---|---|
| 1 | 容器 / 镜像 | `4f387a12e84b` / `strata-gfx906:0.2.10-101`（image `5267df6dbdeb`） |
| 2 | 运行中引擎 | `eea5ea3749ad54b124330386605a18bc`，44,908,992 B（strata 0.1.56，v0.9.0） |
| 3 | config | md5 `e62685e6ff21d9e2b60c1cd622fd5a67`（已恢复到改前逐字节）；exe=`/data/bin/strata-0.1.56-090`；args **37**；env **9** |
| 3a | args 明细（37 项 / 19 个 flag） | `--pack /data/packs/ud-q4_k_xl` `--native /models/…/Qwen3.8-Flash-Next-UD-Q4_K_XL-00001-of-00004.gguf` `--expert-profile /src/data/expert-profile.bin` `--expert-cache auto` `--pcie-frac 0.20` `--spec 4` `--spec-min-p 0.70` `--mtp /data/mtp/rt` `--max-context 262144` `--kv k8v4` `--prefill auto:16384` `--prompt-cache-every 8192` `--expert-profile-save /data/profiles/q4kxl-learned.bin` `--conversation-cache-mib 4096` `--vision` `--mtp-window 8192` `--vram-reserve-mib 832` `--ple-io mmap` `--pool-workers 10` |
| 3b | env 明细（9 项） | `HSA_OVERRIDE_GFX_VERSION=9.0.6` `STRATA_PREFILL_CPU_SHARE=auto` `STRATA_PREFILL_CPU_SHARE_MAX=3072` `STRATA_ROCBLAS_TUNING=…` `STRATA_GFX906_TUNED=1` `STRATA_CKPT_MOVE_PARK=1` `STRATA_DECODE_TIMING=1` `STRATA_SPEC_DEPTH=1` `STRATA_PREFILL_TIMING=1`（本轮试装过 `STRATA_GR_V3=1`，已摘除，见第三节） |
| 4 | 健康 | `/health` ok、`loaded:true`、restarts=0、StartedAt `2026-11-05T15:55:45Z` |
| 5 | 资源隔离 | 容器内 `ulimit -l` = unlimited（host soft/hard = **16,473,712 KB** ≈ 15.7 GiB，更正此前「host unlimited」的说法）；引擎 `VmLck` = 0 kB |
| 6 | 显存布局 | expert cache `7463 slots / 21.79 GiB`、`borrows 2606 (7.62 GiB)`、`882 MiB of VRAM free`（启动横幅，重启后复现一致） |
| 7 | 回滚件 | `strata-0.1.56-080`；**本轮实际用到**：`cp /data/strata-huihui-ud-iq4_xs.json.bak_235103 /data/strata-huihui-ud-iq4_xs.json` → md5 回到 `e62685e6…` |
| 8 | 本轮改动 | config 改过 1 次（`+STRATA_GR_V3=1`）并已逐字节恢复；引擎/镜像/args 未变；disk = build = running = `eea5ea37…` 三方一致 |

**二、主线** gfx906/mi50 @ a872a29d · tag `mi50-0.2.10-r32-18-ga872a29d` · 落后 0 / 领先 0 · 上游 `ffa80d73` · 工作树脏 0 行。
**三、本次落生产** 改动 1 处（已回滚）；重启 3 次；停机合计约 2.5 分钟；回滚件已用（详见第七节事故）；代码面 1 提交 `a872a29d`（6 文件 +452/−46，GitHub run #31 success）。
**四、进度** 254 条 / 已结 174 / **68.5%**；队列 R95（P309 实验）→ R94 → R91 → R89 → R46 → R49 → R50。

---

## 五、R21 排了五轮，它在我们的配置里根本不会执行

`STRATA_GR_V3=1`（hyper-connection read 的流拆分版）是 R21 的排头。开工前先读它的生效条件，一句话就结束：

- `fused_gr.cu:2899` — `split = v3 && a[0].s_down == nullptr && a[0].s_up == nullptr ? split3[dev] : -1;`
- `fused_gr.cu:2903` 注释逐字 — *"it declines Q8 weights (s_down set)"*；`fused_gr.cu:2953` — *"its K-split down reads bf16 rows (not STRATA_HC_REQ8)"*
- `arch_defaults.cpp:221` — gfx906 的 tuned 集合里写死 `STRATA_HC_Q8=1`（KL 0.0011、argmax 100%）

⇒ `s_down != nullptr` 恒成立 ⇒ **v3 在我们这台机器上永不启用**。为确认不是只有源码这么说，仍然开了 A/B（`ci/cfg_apply.py`，冷 prompt，n=6/3）：

| 臂 | prefill@2000 | @8000 | @16000 | decode |
|---|---|---|---|---|
| 基线 `w1013-base` | 513.65 tok/s | 684.62 | 767.22 | 35.82 tok/s |
| `STRATA_GR_V3=1` | 513.66（**+0.08%**） | 684.99（**+0.05%**） | 766.63（**−0.08%**） | 34.40（band 13.98%） |

三档全在带内（0.78 / 1.06 / 0.08%）⇒ 不是「v3 没用」，是**那段代码没跑**。`R21` 判 `DONE_NEG`，`P244` 从 `CANDIDATE` 改 `REJECTED`。真要吃它的并行度，得先给 int8 码写一个 v3——那是 R86 同类的移植，不是开关。

## 六、这一轮最贵的教训：门在装完之后崩了，配置留在线上

A/B 走 `ci/cfg_apply.py`（配置改动的唯一合法通道）。它在**装完候选、重启完、测完之后**崩在判决算术：

```
UnboundLocalError: cannot access local variable 'better' where it is not associated with a value
```

`better` 只在「某长度越过 2×CV」的分支里赋值（原位置 `cfg_apply.py:296`） ⇒ **任何没有明显收益的 A/B（也就是绝大多数）都必崩**，而崩点在回滚之前 ⇒ 候选留在线上、**没有记录、没有回滚**。本轮就是这样把 `GR_V3=1` 留在了生产上，config md5 从 `e62685e6…` 变成 `6626996e…`，发现后 `cp .bak_235103` 恢复回 `e62685e6…`（逐字节）。

它为什么没被当场看见：我把命令接进了 `| tail -26`，管道的退出码是 `tail` 的。**记忆里早有 `PIPESTATUS` 这一条，这次是我自己犯的。**

修复不是补一行：判决算术抽成纯函数 `compare_arms()`（符号按 `prefill_at()` 的量纲——**prompt tok/s，越高越好**，反过来就会把 2% 的收益记成回退）；装完之后整段 `try/except BaseException` ⇒ `cp bak` → 重启 → 写 `*.crash` → **exit 4**，绝不再往下走；`ci/test_cfg_verdict.py` 7 例（含 23:52 那次崩溃形态、无 `--lengths`、符号反向），已进 `round_gate --ci`（`SELF_TEST: 7/7`，见 `round_gate.py:71`）。

## 七、真正该进方案的一条：5% 单条门已经没有东西可筛

这是本轮的主结论，也是它值得写进权威方案的原因——**队列不是被物理堵住的，是被一条判据堵住的**。逐条摆开（份额由 `PREFILL_PHASES.tsv` 的 2K 簇反算，不手打）：

| 条目 | 相位（2K） | 相位 delta | 折算整条 prefill | 依据 |
|---|---|---:|---:|---|
| `R86-dn` down-only 权重 repack | gemm down **510 ms** | −20% | **−3.20%** | bench（`WIDTH_SWEEP.tsv`） |
| `R95-plan` 建组计划挪 issuer | host grouping **91 ms** | −100% | −2.85% | estimate |
| `R21-v3hc` v3 的 int8 版 | hc read: down+silu **117 ms** | −40% | −1.47% | estimate |
| `GDN-chunk` 分块递推 | gdn recurrence **121 ms** | −50% | −1.90% | estimate |
| `R98-wc` 预取深度 | wait copy **37 ms** | −50% | **−0.58%** | estimate |

五条加起来 **−9.99%**，单条最大 **−3.20%**，没有一条过 −5%。所以判据改成组合门：

> 一个 **bundle** 按**它的和**采纳（2K prefill ≤ −5%）；里面每条仍须各自越过 **2×CV**；改舍入的条目由**一份** `Q:` 质量门覆盖整包；`estimate` 只占队列位置，**永不计入和**。

`ci/bundle_budget/bundle.py:141` 把算术做成门：`phase_ms_2k` 必须等于 `PREFILL_PHASES.tsv` 的 2K 簇中位数（±2%，份额不许手打）、`bench` 条目必须越过 2×CV、`ADOPT` 的和不足 −5% 直接 FAIL、证据件必须存在、改舍入的 `ADOPT` 必须有 `Q:` 行。**负向 4/4**（手打份额 / 次 CV 的 delta / 无账的 ADOPT / 不存在的证据）+ **自测 6/6**。当前预算 **0.00/5.0** —— 一条都没采纳，这是实话。

## 八、外网：分块 GDN 的收益是真的，但都骑在矩阵核上

- ONNX Runtime `#32182`：chunked（WY/UT）prefill，Qwen3.8-27B 几何 **4.5×**（T=1024），实现只用 `mma.sync.m16n8k16`（sm_80+ PTX）。
- FlashQLA（Qwen 官方）：对 FLA Triton 前向 **2–3×**，TileLang + warp specialization，Hopper。
- 同一实现的约束：chunk 64×64 需 **157 KB** SMEM，32×64 需 **96 KB**；gfx906 的 LDS 只有 **64 KB**，且**没有矩阵核**（只有 `v_dot*`）⇒ 收益得用 FMA 重算，倍数不能照抄。

⇒ `GDN-chunk` 保持 `BLOCKED`，复谈条件写死：**有人写出 C≤16、≤64 KB LDS 的 FMA 分块内核**，且相位实测 ≥2×CV。`R98` 同时关：37 ms 砍半只有 −0.58%，低于我们任何一道门的噪声底。

## 九、门与同步

`ROUND_GATE: PASS`（`VERIFY` / `PHASES` / `BUNDLE` / `SELF_TEST 7/7` / report_lint 正负自测）；本机 `ROUND_CLOSE` 七项（report 12 字段 / depth / plan A–F / audit_index / plan_retired / pointer / bundle / mirror）。六件权威件双侧逐字节：`W832 83306bb1…`（83,306 B 量级）、`PROGRESS 45cfb549…`、`PARAM_REGISTER 8c406d37…`、`ID_MAP 81891d72…`、`AUDIT_INDEX aa15671c…`、`AUDIT26 5f2f29ed…`。`ledger` 29 项、`param_pair` 15 处均与上轮持平（旧债）。
