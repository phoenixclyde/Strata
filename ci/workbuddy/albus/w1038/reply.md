# W1038 — `--kv int8` vs 在产 `--kv k8v4`：直接换参数跑出来的对比

> 问题：机主 08:30「如果 kv 用 int8 的话，比一下收益呢。我要直接跑出来的数据对比。」
> 做法：只换 `--kv` 一个 CLI 参数，其余 37 个 args / 9 个 env / 二进制 md5 全同；每臂两轮冒烟；跑完**已还原 k8v4**。
> 结论：**int8 在速度上没有收益（8K +0.42%），在显存上是净支出（−240 专家槽 / −0.71 GiB），唯一买到的是质量；质量这一半本轮没测。**

---

**一、生产容器（10 字段，2026-11-07 08:39 只读，还原后）**

| # | 字段 | 值 |
|---|---|---|
| 1 | 容器 / 镜像 | `2d765942e041` · `strata-gfx906:0.2.11-101` · `ulimits.memlock=-1:-1` |
| 2 | 运行中引擎 | `strata-0.1.57-b12180` · md5 `d24f8293b575fbcee6c097239d9599cb` · 43,207,464 B |
| 3 | config | md5 `5e9b81e2f66ca48999766d2ae0201fb6` · `exe=/data/bin/strata-0.1.57-b12180` · args 37 / env 9 |
| 4 | 健康 | `/health` ok · restarts=0 · StartedAt `2026-11-07T00:37:41Z`（= 08:37:41，**还原 k8v4 后的启动**） |
| 5 | 资源隔离 | `VmLck 0 kB` · `ulimit -l` unlimited · `memlock=-1:-1` |
| 6 | 显存 | used 33,495,166,976 / total 34,342,961,152 ⇒ **VRAM free 847,794,176 B（0.79 GiB）**；expert cache **7463 槽 / 21.79 GiB**；the prompt path borrows 2606 槽（7.62 GiB） |
| 7 | 回滚件 | `/data/bin` **49 件** · `b12180`（在产）→ `k10p`（`e0a6987f…`）→ `-001`（`5e63174d…`） · `ci/rollback.sh` · config 备份 `tmp/w1038/cfg_kv.bak` |
| 8 | 本轮改动 | 引擎**无净变更**：disk = build = running 三方一致（`b12180` / `d24f8293…`）；config 改过一次 `k8v4 → int8` 又**逐字节还原**（md5 回到 `5e9b81e2…`）；**重启 2 次、停机 90 s**、装机 0、回滚 0 |
| 3a | args 明细 | 37 项；本轮只有 `--kv` 一项被改过并已逐字节还原（`k8v4` → `int8` → `k8v4`）：`--pack` `--native` `--expert-profile` `--expert-cache` `--pcie-frac` `--spec` `--spec-min-p` `--mtp` `--max-context` `--kv` `--prefill` `--prompt-cache-every` `--expert-profile-save` `--conversation-cache-mib` `--vision` `--mtp-window` `--vram-reserve-mib` `--ple-io` `--pool-workers`（19 个 `--flag`） |
| 3b | env 明细 | 9 项，本轮未动：`HSA_OVERRIDE_GFX_VERSION=9.0.6` `STRATA_PREFILL_CPU_SHARE=auto` `STRATA_PREFILL_CPU_SHARE_MAX=3072` `STRATA_ROCBLAS_TUNING=/data/gfx906-rocblas-5.7.0.txt` `STRATA_GFX906_TUNED=1` `STRATA_CKPT_MOVE_PARK=1` `STRATA_DECODE_TIMING=1` `STRATA_SPEC_DEPTH=1` `STRATA_PREFILL_TIMING=1` |
| 9 | ROCm | 10.1.0 · HIP 7.16.26323-0000000 · clang 24.0.0git |
| 10 | llama.cpp | b12180 = `bcb0152876e8f0b684ba70d3defcab6cdf35adb5`（2026-11-06T22:42:46Z） + `mmq*` @ `4c1004c` |

**二、主线** — `gfx906/mi50` @ e181bda5（`mi50-0.2.11-r33-14-2-ge181bda5`，落后上游 0 / 领先 80，脏 0 行）。实验分支 `gfx906/lcpp-k10` @ `fa8e6761`（已推 origin），`gfx906/port-all` 工作树有一个未提交改动（OPT 接线）。

**三、本次落生产** — **重启 2 次 / 停机 90 s（45+45）/ 回滚 0 次 / 装机 0 次**。窗口 08:34:47–08:38:27：停容器 → 改 `--kv int8` → 起（health 45 s）→ 测 → 停 → 还原 config（md5 校验 `5e9b81e2…`）→ 起（health 45 s）。当前在产仍是 `b12180` + `k8v4`。

**四、进度** — **387 条 / 已结 302 / 78.0%**（本轮 +4：`P442` / `P443` / `P444` / `R104`）。队列：`R104`（新，`--kv-grow`）→ `R103` → `R95` → `R94` → `R91` → `R89` → `R46` → `R49` → `R50`。

---

## 一、直接换参数跑出来的数（同机 / 同二进制 / 同 prompt / 两轮）

臂：ctl = `--kv k8v4`（在产，不重启）；b = `--kv int8`。两臂各跑两轮 `ab_w1037.py`（2.5K×3 + 8K×2 + decode×3），合并 2.5K n=6 / 8K n=4。

| 轴 | `k8v4` | `int8` | Δ | 2×CV |
|---|---|---|---|---|
| prefill 8K µs/tok | **1250.9**（CV 0.24%） | **1256.2**（CV 0.24%） | **+0.42%** | 0.48% |
| prefill 2.5K µs/tok | 1565.5（CV 0.96%） | 1585.6（CV 2.39%） | +1.29% | 4.78% |
| 8K `qsa attn` (ms) | 2237.5 | 2245.5 | +0.36% | — |
| 8K `gemm gate/up` | 2653.0 | 2643.0 | −0.38% | — |
| 8K `gemm down` | 1672.8 | 1671.5 | −0.08% | — |
| 8K `dequant` | 520.5 | 514.8 | −1.09% | — |
| decode tok/s | 62.90（CV 10.8%） | 59.40（CV 6.7%） | −5.56%（中位 −4.21%） | 不可分 |
| **专家槽 / 专家池** | **7463 / 21.79 GiB** | **7223 / 21.08 GiB** | **−240（−3.2%）/ −0.71 GiB** | 直接量 |

2.5K 的 +1.29% 是一个冷启动样本拉起来的：int8 第一个样本 1661.8 µs/tok，其余五个 1563.6 / 1566.2 / 1566.7 / 1573.6 / 1581.9，剔除首样本后 +0.3%。
8K 的 +0.42% 不但没被 2×CV 盖住（0.48%），反而是这轮唯一"擦边"的数——但它只有 5 ms 的量级，且同臂四个样本方向一致，我按**微负**记，不按显著记。

## 二、为什么 attention 的时间压根不动（源码给的是必然）

`kv_q8.hpp:33` 的 `kv_gather_q8_step` 与 `kv_q4.hpp` 里 Q4 的 gather，**都把选中的 cell 反量化进同一块 FP16 scratch**，attention 内核读到的输入类型、布局、元素值域完全一致 ⇒ 后端那段 fp32 `fmaf` 的指令数与计算量不变。
换 KV 格式改变的只有 gather 的字节数：V 侧 528 B/cell（int8）对 288 B/cell（q4_0），K 侧两者相同（都是 int8）。
而 8K、10756 tok 的整条 prefill 是 13516–13680 ms，`qsa attn` 只有 2237 ms（16.5%），gather 在这 2237 ms 里又只占零头 ⇒ 净效应必然落在 0.4% 以内。

**这条推论可以复用**：只要 KV 是"gather 后反量化再算"，**KV 位宽就不是速度旋钮，只是显存旋钮**。想让它变成速度旋钮，得让 attention 直接吃 int8 做 `sdot4`（`R64`，dp4a 目前 0 处）——那是另一条路，不是换参数。

## 三、显存差被两个独立口径同时钉住（顺带结掉一个旧错账）

- **源码算术**：`kv_q8_bytes_per_cell`（`kv_q8.hpp:25`）= `n_head_kv*head_dim*2 + n_head_kv*(head_dim/64)*2*2` = 2×256×2 + 2×4×2×2 = **1056 B/cell**；k8v4 = int8 的 K（528）+ q4_0 的 V（288）= **816 B/cell**。× 262144 cells × **12 层 QSA**（`kv_q8.hpp:3`）= 3.094 GiB 对 2.391 GiB，差 **754,974,720 B = 720.0 MiB**。
- **实测行为**：`--kv int8` 启动后专家池 21.79 → 21.08 GiB、槽 7463 → 7223；槽均价 21.79 GiB ÷ 7463 = 2.990 MiB ⇒ 240 槽 = 0.701 GiB。

两条路径 720.0 vs 701 MiB，偏差 1.3%（GiB 四舍五入造成的），**互为独立验证**。
顺带把旧账「k8v4 比 int8 省 3.8 GiB / 1700 槽」判为错：那个量级对应的是 **fp16→int8**（992 B/cell），不是 k8v4→int8（240 B/cell）。

## 四、这轮量出来的副产品：KV 是按 `--max-context` 全额预分配的

上面"KV 多 720 MiB ⇒ 专家槽少 240"的一一对应，本身就证明了一件事：**KV 不是按需长，是开局就按 262144 cells 占满的**。

| 格式 | B/cell | KV 全额 @262144×12 |
|---|---|---|
| fp16 | 2048 | 6.000 GiB |
| int8 | 1056 | 3.094 GiB |
| **k8v4（在产）** | **816** | **2.391 GiB** |
| q4_0 | 576 | 1.688 GiB |

`--kv` 的帮助文本（`generate.cpp:1058`）自带一个 `--kv-grow`：*"the K/V takes VRAM only for the cells the requests reach and the expert cache holds the rest, giving slots back as the context grows (one GPU, with --expert-profile)"*，而默认正是"the whole --max-context allocated at start"。
我们有 `--expert-profile`（前置满足）。典型 8K–16K 实际用到时 KV 只需 0.08–0.15 GiB ⇒ 可让出 **2.24–2.31 GiB ≈ 770–790 槽（+10.3%–10.6%）**，比 int8↔k8v4 那 240 槽大一个量级。已立 `P444` / `R104`，排在 `R103` 之前。

## 五、没测的那一半，说清楚

**质量本轮没测。** KL / top-1 需要 LOGPOS 探针独占窗口，这轮只开了一个 90 秒的性能窗口。
账本里 `0.0416`（int8）对 `0.0704`（k8v4）是旧测，且 `AUDIT24` 自己标了"需复核"，**我不拿它当依据**。
能核的是仓库里的 `bench/results/2026-09-27-kv-q4/README.md`：int8 与 fp16 在四种文本上都落在 2 个标准误内；`q4_0` 在 8K 上 KL 是 int8 的 4.2×、ppl +12%。k8v4 的 V 就是那个 q4_0 ⇒ "int8 质量更好"方向可信，**幅度待测**。

## 六、判决

**保持 `k8v4`。** 理由是按轴算清的，不是印象：

- 速度：int8 无收益（8K +0.42%、2.5K +0.3% 剔除冷启动、`qsa attn` +0.36%），decode 方向微负且在噪声带内；
- 显存：int8 净支出 720 MiB = 240 槽（−3.2%）；
- 质量：int8 更好，但本模型上没测。

**如果质量是刚需**（比如长文档 8K+ 的检索精度），那就该开一次**数值窗口**把 KL 量出来再定，而不是拿速度窗口顺手定质量——那正是 `P392` 犯过的错。
**如果目标是"多拿性能"**，`R104`（`--kv-grow`）才是那个数量级的开关：一次重启、零代码、770+ 槽。

---

**产物**：`albus/w1038/reply.md`（本件）、`albus/w1038/kv_ab.sh`（窗口脚本，含改参/健康/还原/快照）、`albus/w1038/append_ledger.py`、`deploy/W832_OPT_PLAN_V2.md`（§0.1 队列 + 回写 W1038）、`deploy/PROGRESS.tsv`（`P442`–`P444`）。
**原始数据**：166 上 `/home/albus/strata166/tmp/w1038/arm_kv_{k8v4,k8v4b,int8,int8b}.json` 与 `kvab.log`。

---

## 附：本轮 config 明细（未变，逐项列出，便于与上一轮逐字对差）

`args`（37 项，`--kv` 为本次唯一改动项，已还原）：

`--pack /data/packs/ud-q4_k_xl`、`--native /models/huihui-ai/Huihui-Qwen3.8-Flash-Next-abliterated-GGUF/unsloth-UD-Q4_K_XL/Qwen3.8-Flash-Next-UD-Q4_K_XL-00001-of-00004.gguf`、
`--expert-profile /src/data/expert-profile.bin`、`--expert-cache auto`、`--pcie-frac 0.20`、`--spec 4`、`--spec-min-p 0.70`、`--mtp /data/mtp/rt`、
`--max-context 262144`、`--kv k8v4`、`--prefill auto:16384`、`--prompt-cache-every 8192`、`--expert-profile-save /data/profiles/q4kxl-learned.bin`、
`--conversation-cache-mib 4096`、`--vision`、`--mtp-window 8192`、`--vram-reserve-mib 832`、`--ple-io mmap`、`--pool-workers 10`
（以上为 `--flag` 形态的 19 个；其余 18 项为其取值与 `--serve` 等开关，合计 37。）

`env`（9 项）：

`HSA_OVERRIDE_GFX_VERSION=9.0.6`、`STRATA_PREFILL_CPU_SHARE=auto`、`STRATA_PREFILL_CPU_SHARE_MAX=3072`、
`STRATA_ROCBLAS_TUNING=/data/gfx906-rocblas-5.7.0.txt`、`STRATA_GFX906_TUNED=1`、`STRATA_CKPT_MOVE_PARK=1`、
`STRATA_DECODE_TIMING=1`、`STRATA_SPEC_DEPTH=1`、`STRATA_PREFILL_TIMING=1`
