# W1041 报告 · R103 重开：换掉那把量尺之后，DP4A 从「不可测」变成「比现役 KV 档还便宜」
> 一句话：**同一对臂，旧门读 0.04，新取样面读 0.0034——差一个量级**。换成 R104 的 fp32 全词表 logits 直比、
> 并加一条**锚臂**（把 KV 存成 fp16，也就是我们为了省显存放弃的那一档）之后，攻击向量的结论翻过来了：
> **`ATTN_DP4A` 的数值代价在四个长度上全部小于我们已经接受的那一档**，而它同时把 attn 打掉 **10.2–11.4%**、整条 prefill **1.0–2.3%**。

---

**一、生产容器（10 字段，2026-11-07 14:44 只读）**

| # | 字段 | 值 |
|---|---|---|
| 1 | 容器 / 镜像 | `2d765942e041` · `strata-gfx906:0.2.11-101` · restarts=0 · StartedAt `2026-11-07T06:40:45Z`（= 14:40:45，D 臂还原后那次启动） |
| 2 | 运行中引擎 | `strata-0.1.57-kvg` · md5 `a85743d7f554159e8ac1e2d432d2e5ea` · 43,214,976 B（**本轮未换件**） |
| 3 | config | md5 `ee69ebc272ce41a116f50ecb3bf0edc2` · `exe=/data/bin/strata-0.1.57-kvg` · args 38 / env 9（**本轮未改**） |
| 4 | 健康 | `/health` `{"status":"ok","loaded":true}` · restarts=0 |
| 5 | 资源隔离 | `VmLck 0 kB` · `ulimit -l` unlimited · `memlock=-1:-1` |
| 6 | 显存 | used **33,493,712,896** / total 34,342,961,152 ⇒ **VRAM free 849,248,256 B（0.79 GiB）**；expert cache **8301 槽 / 24.23 GiB**；the prompt path **borrows 2609 slots (7.62 GiB)** |
| 7 | 回滚件 | `/data/bin` **53 件** · 上一版 `b12180`（`d24f8293…`）→ `k10p` → `-001`；本轮四臂用的 `pa5`（`c639b60c5981267c8d82ee3a4b0750e8` / 43,475,584 B）也在册；rollback = 停容器 → `cp` 回 `tmp/w1040/cfg_w1040.bak` → 起容器（≈45 s） |
| 8 | 本轮改动 | **引擎无变更、config 无变更、disk = build = running 三方一致**（`docker exec md5sum /data/bin/strata-0.1.57-kvg` = `a85743d7…`）；只是停/起了两次跑四臂：**重启 2 次 / 停机 549 s / 装机 0 / 回滚 0** |
| 3a | args 明细 | 38 项（生产，**本轮未改**）：`--serve` `--pack` `--native` `--expert-profile` `--expert-cache auto` `--pcie-frac 0.20` `--spec 4` `--spec-min-p 0.70` `--mtp` `--max-context 262144` `--kv k8v4` `--prefill auto:16384` `--prompt-cache-every 8192` `--expert-profile-save` `--conversation-cache-mib 4096` `--vision` `--mtp-window 8192` `--vram-reserve-mib 832` `--ple-io mmap` `--pool-workers 10` `--kv-grow`；四臂跑的是**副本** （`tmp/w1041/cfgA–D.json`：去掉 `--kv-grow`、`--expert-profile-save` 指到 `/w/`） |
| 3b | env 明细 | 9 项全部未改：`HSA_OVERRIDE_GFX_VERSION` `STRATA_PREFILL_CPU_SHARE` `STRATA_PREFILL_CPU_SHARE_MAX` `STRATA_ROCBLAS_TUNING` `STRATA_GFX906_TUNED` `STRATA_CKPT_MOVE_PARK` `STRATA_DECODE_TIMING` `STRATA_SPEC_DEPTH` `STRATA_PREFILL_TIMING`；四臂的开关只加在**容器内**：C 臂 `STRATA_GFX906_ATTN_DP4A=1`、D 臂 `QQ_KV=fp16`（取样面的 `--kv` 覆盖，不是生产配置） |
| 9 | ROCm | 10.1.0 · HIP 7.16.26323-0000000 · clang 24.0.0git |
| 10 | llama.cpp | b12180 = `bcb0152876e8f0b684ba70d3defcab6cdf35adb5` + `mmq*` @ `4c1004c` |

**二、主线** — `gfx906/mi50` @ e181bda5（`mi50-0.2.11-r33-14-2-ge181bda5`）；**生产源码树 `pr/k10` @ af797b90，相对 `origin/gfx906/mi50` 领先 2 / 落后 0，脏 0 行——本轮一个行都没改**；上游 `upstream/main` 本轮未重算（`ghup` remote 只读、`upstream` 走 gh-proxy，上次读数是 behind 0），换基线是另一件事，不在本轮。实验树 `pr/port-all` @ 91a7c5a4（脏 10 行，是 pa6–pa8 的遗留实验改动，未提交、与本轮结论无关）；`pa5` 二进制来自该树，**只当被测件**，没有进生产。

**三、本次落生产** — **零**：引擎未换件、config 未改字节（`ee69ebc2` 全程不变）。本回合 **重启 2 次 / 停机 549 s / 装机 0 / 回滚 0**（四臂窗口 14:32:01→14:38:22 = 381 s，补 D 臂 14:38:43→14:41:31 = 168 s；两次都是「停 → 跑臂 → 起回同一份 config」）。停机全部花在四臂占 GPU 上，没有一次是装机。

**四、进度** — **443 条 / 已结 354 / 79.9%**（本轮 +2：`P497` 预注册、`P498` 判决）。队列：**R103（重开已判、待移植）** → R106（`gen_config` 工具链）→ R107（`AUDIT29`）→ R105（`hipk`）→ R95 → R94 → R91 → R89 → R46 → R49 → R50。

---

## 正文

**1. 先回答「四项报告没了」**

上一轮我把它写进了 `albus/w1040/reply.md`，但**回复里只给了摘要**——这就是你说的「没了」。本轮的规矩改掉：**四件套直接放回复开头**（一、生产容器 10 字段 / 二、主线 / 三、本次落生产 / 四、进度），文件只当留档。

**2. 重开 R103 的第一件事：换尺，不是翻案**

`P467` 当时把 attn 一支结案成「现有数值门不可测」，理由是七组两两 KL 全在 0.0354–0.0465，**连两个逐位相同的臂都「有 0.04」**，而探针证明读法与算术只差 1e-6。那结论是对的——**错的是尺**。R104 交出来的替代取样面是 `STRATA_DUMP_FIRST_LOGITS` 的 float32 全词表 logits（993,280 B/个）：能 `cmp -s` 逐字节比，也能算概率加权的差。

同一对臂（C = `pa5`+`DP4A` vs A = `b12180`）：**旧门 0.04，新取样面 8K 上 0.00345**。差一个量级 ⇒ 0.0139 这个阈值只对那台仪器成立，**不能跨仪器引用**。

**3. 外证：先把「别人的数」和「我们的数」摆在一起，再决定要不要引用**

| 来源 | 改动 | KL（nats） | top-1 |
|---|---|---|---|
| rx7900xtx `kv-quality.md`（llama.cpp，同族） | KV q8_0 vs f16 | **0.000587** | 98.76% |
| 同上 | KV q4_0 vs f16 | 0.002450 | 97.38% |
| sergiiob（KV 量化专题） | K=Q5_0 | ~0.008 | — |
| 同上 | K=Q4_0 | **>0.03「破坏」** | — |
| hotdry（运维阈值建议） | attention 分布 | **>0.05 视为可感知退化** | — |
| **我们 `P04`（W767，旧仪器）** | **k8v4 vs f16** | **中位 0.0704** | 81.92% |

**我们自己的 KV 档在旧仪器上读 0.0704，比社区的 q5_0 大一个量级** ⇒ 「我们的 KL 轴与社区不是同一把尺子」这件事，本轮之前只是怀疑，现在有数了。所以判据不能引用 0.0139 或 0.05，只能**自带锚**。

**4. 四臂与 build floor**

| 臂 | 二进制 | 开关 | 作用 |
|---|---|---|---|
| A | `b12180` | — | 基线（k8v4） |
| B | `pa5` | 无 | **build floor**：只换树不加开关 |
| C | `pa5` | `STRATA_GFX906_ATTN_DP4A=1` | 被测（`P452` 的 −11.3% 那一支） |
| D | `b12180` | `--kv fp16` | **锚**：我们为省显存放弃的那一档 |

**B 与 A 四个长度全部逐字节相同**（`cmp -s` IDENT）⇒ C 的差异里没有「换了棵树」的成分。这一条如果不成立，整轮作废——它是预注册的第①条。

**5. 判决数据：C 在四个长度上全部优于锚 D**

| 长度 | 参考分布 p(top1) / 熵 | **C：KL** | **D：KL** | C 比 D 好 |
|---|---|---|---|---|
| 1000 | 0.996 / 0.03 | **0.00037** | 0.00155 | **4.2×** |
| 8000 | 0.988 / 0.11 | **0.00345** | 0.01113 | **3.2×** |
| 16000 | 0.993 / 0.05 | **0.01429** | 0.01699 | **1.19×** |
| 20000 | 0.683 / 0.83 | **0.18750** | 0.38387 | **2.05×** |

**这张表的读法**：D 是「把 KV 存成 fp16」——同性质、同方向的取舍，而我们为了显存一直在用更省的 k8v4。**C 的代价小于我们已经接受的那一档**，所以预注册的第③条成立。KL_top64 与全词表 KL 几乎相同（0.00037/0.00291/0.01388/0.18727），说明差量集中在**真正有概率质量的那几十个 token**上，不是尾部噪声。

**6. 性能：同一次 run 里就有的数，不用另开窗口**

| 长度 | `qsa attn` B → C | Δ | 整条 GPU timeline B → C | Δ |
|---|---|---|---|---|
| 1000 | 74 → **66** ms | −10.8% | 5440 → **5384** | −1.03% |
| 8000 | 1585 → **1404** | −11.4% | 10635 → **10394** | −2.27% |
| 16000 | 3424 → **3050** | −10.9% | 21622 → **21211** | −1.90% |
| 20000 | 4359 → **3914** | −10.2% | 30722 → **30338** | −1.25% |

这复现了 `P452`（attn −11.3% / 整条 −1.78%）。顺带一个对照：**D 臂的 attn 是 +42%**（2267 / 4861 / 6170 ms）——fp16 KV 让 attention 每次多读一倍字节，这正是我们当年选 k8v4 的原因；也说明「数值上更贵的那一档同时也更慢」，C 是「更便宜且更快」。

**7. 我错在哪（两条，都写在账上）**

- **第一指标选错了**：我预注册 `max|Δlogit|` 当第一判据，实测 C/D 都在 **3.3–4.8 nats**，而同期 KL 只有 0.0004–0.19。原因是极值落在**概率质量几乎为零的尾部 token**上。⇒ 决策量必须概率加权（KL / top-64 KL / top-10 重合），`max|Δ|` 只能当「有没有病态大偏差」的报警器。这与 `P485`（中位数不可除）、`P493`（取样面错）同族：**先定对量的定义，再谈阈值**。
- **预注册的 top-1 条件没达标，不略过**：20000 那点 C 与 D **都翻了 argmax**，而该点参考分布本身是近掷硬币（p(top1)=0.683、top1−top2 裕度 0.42、熵 0.83 nats）；1K/8K/16K 两臂都保持 argmax。单点翻面不足以下质量结论，但**按字面判据就是不达标**。外部实测也正好支持这条：perplexity 平、KL 均值 <0.01 时答案翻转率仍可到 5%（technolynx 2026）。**处置**：装机前补一道**任务级门**（R104 用过的 28,695 token needle + 16K 档），不再拿「一个位置的 argmax」当质量结论。

**8. 下一步：移植不是 cherry-pick，别把它当一行改动**

`port-all` 与 `pr/k10` 的 `src/kernels/cuda/qsa_decode_attn.cu` 已明显分叉：port-all 那份多了 DPP 模板（`dpp_xor1` 一族）、`dp4a.hpp` 头、warp-per-group 量化整段（`src/kernels/cuda/qsa_decode_attn.cu:245` 起，注释写着「Pattern copied from llama.cpp's quantize_q8_1」），派发宏在 `src/kernels/cuda/qsa_decode_attn.cu:1168`（`STRATA_ATTN_OPT_DISPATCH`）与 `src/kernels/cuda/qsa_decode_attn.cu:1189`（`..._SWZ`），开关解析在 `src/kernels/cuda/qsa_decode_attn.cu:1136`（`gfx906_attn_opt`），bit1 的语义写在 `src/kernels/cuda/qsa_decode_attn.cu:178`。k10 那份这些都没有 ⇒ **要真合并**，不能 `git cherry-pick`。

顺序（下一轮）：① 把 OPT 那几段搬进 `pr/k10`（`af797b90` 之上新分支）；② 建 `kvg+dp4a` 候选；③ **先用本轮同一取样面验 floor**（`kvg` 无开关 ≡ `kvg`，四个长度逐字节）；④ 任务级门（28,695 token needle + 16K）；⑤ 生产 A/B（同 exe 开关对比，`P486` 的 pass 对称协议）；⑥ 装机。

**9. 原始产物** — 166 `tmp/w1041/`：`qq_r103.py`（取样面，四长度 + `QQ_KV` 覆盖）、`set20k.ids.json`、`cfgA–D.json`、`lg_A/` `lg_B/` `lg_C/` `lg_D/`（各 4 个 `first.*` + `index.json` + `stderr.txt`）、`window.log`、`window_d.log`、`cmp_logits.py`、`diag_logits.py`；本机 `albus/w1041/`：`prereg.py`（跑之前写死的判据）、`land_verdict.py`、`land_plan.py`、`window_r103.sh`、`window_d.sh`、`run_window.py`、`cmp_logits.py`、`diag_logits.py`。
