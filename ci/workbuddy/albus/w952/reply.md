## 一、生产容器（8 字段）

| # | 项 | 值 |
|---|---|---|
| 1 | 容器 / 镜像 | `4f387a12e84b` / `strata-gfx906:0.2.10-101`（image `5267df6dbdeb`） |
| 2 | 运行中引擎 | `ae085365441381c438b56bcabcccf450`，42,924,432 B，`strata 0.1.56` |
| 3 | **config** | md5 `24d66f6a86d7b75f58015efa38d462d2`；exe=`/data/bin/strata-0.1.56`；**args 33 条**；**env 9 条** |
| 3a | args 明细 | `--pack /data/packs/ud-q4_k_xl` `--native …UD-Q4_K_XL-00001-of-00004.gguf` `--expert-profile /src/data/expert-profile.bin` `--expert-cache auto` `--pcie-frac 0.20` `--spec 4` `--spec-min-p 0.70` `--mtp /data/mtp/rt` `--max-context 262144` `--kv k8v4` `--prefill auto:16384` `--prompt-cache-every 8192` `--expert-profile-save /data/profiles/q4kxl-learned.bin` `--conversation-cache-mib 4096` `--vision` `--mtp-window 8192` `--vram-reserve-mib 832` |
| 3b | env 明细 | `HSA_OVERRIDE_GFX_VERSION=9.0.6` `STRATA_PREFILL_CPU_SHARE=auto` `STRATA_PREFILL_CPU_SHARE_MAX=3072` `STRATA_RESIDENT_HEADROOM_GIB=0.5` `STRATA_ROCBLAS_TUNING=/data/gfx906-rocblas-5.7.0.txt` `STRATA_GFX906_TUNED=1` `STRATA_CKPT_MOVE_PARK=1` `STRATA_DECODE_TIMING=1` `STRATA_SPEC_DEPTH=1` |
| 4 | 健康 | `/health` status=ok、`loaded:true`、restarts=0、StartedAt `2026-11-04T08:14:34Z`、max_context 262144 |
| 5 | 资源隔离 | `ulimit -l = unlimited`、`VmLck 28,125,140 kB` |
| 6 | 显存布局 | `expert cache 7463 slots / 21.79 GiB`、`borrows 2606 slots (7.62 GiB)`、`VRAM free 882 MiB` |
| 7 | 回滚件 | 容器 `strata166-407.pre-210`、引擎 `strata-0.1.55w`、`ci/strata-ci rollback --exe strata-0.1.55w --apply` |
| 8 | 本轮改动 | **零**；disk = build = running = `ae085365…` 三方一致 |

## 二、主线（6 项）

`gfx906/mi50 @ 5f73cd15` · tag `mi50-0.2.10-r28` · 上游 `ffa80d73`（v0.2.10）· 落后 0 / 领先 37 · 工作树脏 0 行 · 与 origin 同点。

## 三、本次落生产（4 项）

改动 **零**；回滚命令 `cp /data/strata-huihui-ud-iq4_xs.json.bak_w941 …/strata-huihui-ud-iq4_xs.json && docker restart strata166-407`；重启 **1 次**（为复测 67.3% 停服），停机 **≈4 分 20 秒**。

## 四、进度（4 项 + 队列）

**175 条 / 已结 101 / 57.7%**；主线 147 / 101 / 68.7%；死块池 0/28。
队列：R90-S1（先建 pin→tag 映射，再下 b12099）→ R91-P1（dot8 量化器）→ R91-P3（vec_dot + ISA 断言）→ R91-P4（KL 门，不过即停）→ R88（异步拷贝）→ R86（Q5_1 repack 两臂）→ R87（q8_1 复用）→ R64（Q·K int8）→ R63（readfirstlane 实跑）→ R60（stream-k 实跑）→ R81 → R79 → R80 → R49 → R50 → R30′

---

## 审计范围与结果

**W900–W951 共 50 件，此前一件都没被任何 `AUDIT*` 覆盖**（索引停在 W897）。判据：`AUDIT24` = **P0 2 / P1 16 / P2 12 / 需复核 4**，P0 与 P1 已全部回写（源头横幅、账本行、方案表三处）。

**两条 P0 都会改结论方向：**

1. **W909 把我们专家的量化格式认错了**。它用日志里 `MMQ tile: type 20/21/23` 断言"专家是 IQ4_NL/IQ3_S/IQ4_XS"，并据此否掉 dot8。实测：那 20 行是**能力表**（4 类型 × 5 个 cap，一次打完）；权威来源是 pack 描述符，且**算术精确闭合**——Q4_K gate/up 1,843,200 + Q5_1 down 1,228,800 = **3,072,000 B/专家**，正是描述符里 43 层的 `blob_bytes`。⇒ 专家是 **Q4_K×47 + Q5_K×1 / Q5_1×43 + Q8_0×5**，没有 IQ 码本类型，"dot8 用不上"那条否决不成立（R84/R91 已在办）。
2. **方案本体落后于账本**：`W832` 仍写「MMQ 五扇门（含 R60/R63/R84）全关」「dp4a 53.3%」「R84 −3.65%」，而账本里 R60/R63 = OPEN、R84 = INFLIGHT。已回写 5 处（md5 锚点 `f40c8f39`，行 638/641/655–666/803）。

**P1 里最值得记住的四条：**

- **W944 的 88.6% 是错的**：按 offset 列加权、且分母是"down 的字节"。真值：Q5_1 占**专家总字节 35%**（27.05/77.0 GB）、down 内 86%、层数 43/48；「60.5 GB blob」应为 **77.0 GB**。R86 的端到端预期不变（down 占 prefill 13.8% 才是分母）。
- **W945 的 PMC 数字要带形状**：`MemUnitStalled 0.36%` 是 16×320（生产形状）；同一支 bench 在 16×1024 上是 **9.1–9.6%**（本轮实测）。「MMQ 不是访存受限」只在生产形状成立。
- **W946 的 796→1251 混了两个基线**：README 原文 796 是"一 slot 起点"，1251/1561/1977 的对照列是 887/867/877 ⇒ 正确增益是 **+41% / +80% / +126%**，不是 +57%。
- **W948 的版本判据无效**：`get_J_max` 在**上游 master 也是 0**（只有我们 pin 有 1 处，是自家补丁）；`3cf03257` 只出现在别人的 bench README ⇒「三家 fork 比我们旧」没被源码建立，R90 仍可做，但 S1 必须先建 pin→tag 映射。

## 三条我自己复跑的（不是引用）

| 项 | 结果 |
|---|---|
| W942 的 `VALUBusy 67.1%` | 同形状重跑 **64.78/68.15/68.18/68.17，均值 67.3%** ⇒ 成立（CSV 留 `data/w952pmc/`；原 `data/w941pmc2` 已被 Q5_1 run 覆盖） |
| W945 的 58.0% / 0.36%、60.6% / 0.11% | 用留存 CSV 重算 = 均值 **58.12/0.353**、**60.71/0.109** ⇒ 逐项对上（报告取 4 次 dispatch 均值） |
| W941 的 800+ | 生产日志原样：`60330 … 75030 ms (804.1 tok/s)`、`60008 … 74987 ms (800.2)`，`0 reused` |

外网核对两次：上游 `b12099` = `2026-11-04T05:47:21Z` 发布（b12098/b12097 同日）；furnace README 还确认它自己跑的是 **`-b 16384 -ub 1024` + `GGML_CUDA_REPACK_Q5_1=1`** —— 与我们 chunk 16384、Q5_1 主格式**两处独立吻合**。

## 顺带修的两处机械债

- 账本 **R53/R54 的证据列写成了 `1`**（正文整段挤在 ref 列）——已恢复（273 / 3,822 字）。新增 `tools/ledger_lint.py`（纪律㉑）。
- `W832` 有 **12 行 `\|Δ\|` 未转义**，把 5 列表格撑成 7–9 格（渲染错乱但不报错）——已转义，R89 行两个错格改成真实判据；另有 26 行属老表整表 7-vs-6 漂移，**记为已知未擅改**（纪律㉒）。
