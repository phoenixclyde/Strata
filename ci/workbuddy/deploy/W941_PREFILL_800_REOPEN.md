# W941 · "prefill 800 多"那条：先证它在生产，再把它重开成一条战线

- 日期：2026-11-04 13:2x–14:3x
- 触发：机主「昨天有一个 prefill 做到 800 多，你回滚了。你重开。」
- 结论先行：**800+ 没有被回滚 —— 它是 `--prefill auto:16384` 的效果，此刻仍在生产；本轮复测 801.4 tok/s（0 reused，CV 0.1%）。回滚的是同一次实验里的「三补丁引擎」，它在同样的 801 上零贡献。**
- 但机主要的方向成立：prefill 吞吐在队列里**没有独立条目**（只有 R60/R61 间接路径）⇒ 本轮立 **R85**，并已把 32768 chunk 反证、R61 工具门打通。

---

## 1 事实核对：801 从哪来，什么被回滚

`W932` 的四个臂（全部 `0 reused`，64K 档）：

| 配置 | chunk | borrows | 64K TTFT | 吞吐 |
|---|---|---|---|---|
| 8192 无补丁 | 8192 | 1578 | 81.493 s | 752 |
| 8192 + 三补丁 | 8192 | 1226 | 81.344 s | 753 |
| 16384 无补丁 | 16384 | 2606 | 76.557 s | **801** |
| 16384 + 三补丁 | 16384 | 1904 | 76.451 s | **801** |

- **801 是 chunk 16384 给的**（相对 8192 的 752 = **+6.5%**），这一项**已采纳、在生产**。
- 被回滚的 `9d9cbe17` 是「三补丁」（`PF_GROUP_SCRATCH` / `PREFILL_ROUTED_STREAM` / `PF_HC_REGION`）：它把 borrows 降 27%，但两种 chunk 下 TTFT 都没动（−0.14%，噪声内）⇒ 回滚它不损失任何吞吐。
- 唯一"损失"是它省下的 1.03 GiB 显存没被利用 —— 那是 **R72**（扩 expert cache），与 prefill 速度无关。

**本轮复测（生产原样，未改任何参数）**：

```
prefill rep1  ttft 75.157 s  prompt_tokens 60330
prefill rep2  ttft 75.067 s  prompt_tokens 60008
PREFILL ttft median 75.112 s  CV 0.1%  (~801 tok/s)
engine log: prompt 60330 tokens = 0 reused + 60330 read in 75030 ms (804.1 tok/s)
engine log: prompt 60008 tokens = 0 reused + 60008 read in 74987 ms (800.2 tok/s)
```

⇒ **800+ 在生产、可复现、CV 0.1%**。这一条不必"重开"，需要的是**往上推**。

---

## 2 重开的正确内容：R85（prefill 吞吐台阶）

| 项 | 内容 |
|---|---|
| 现状 | 长档（>32K）**801 tok/s**；16K 档 759；6.4K 档 722；短档（<1K）不是地板（W832）× |
| 目标 | 长档 **≥ 850 tok/s**（+6%，= 2×CV 门以上），且中短档不劣化 |
| 已封的路 | chunk 32768 @64K = **750 tok/s（−6.4%）**，见 §3；chunk 8192 = 752（−6.2%） |
| 剩下的路 | ① **MMQ 供给率**（R61 → R60）：生产折算 4.55 / 21.52 TMAC/s = 21%；② attention int8（R64，长档 15–19%）；③ dot8（R84，上限 3.22%） |
| 判据 | 每个数据点必须 `0 reused`；`|Δ| ≥ 2×CV`（当次 run）；形状写清（chunk / prompt 长度 / T） |

为什么把 R85 单列而不是并进 R60：R85 是**验收口径**（端到端吞吐），R60/R61 是**手段**。没有 R85 时，R60 的"不做"就没有替代路径可走，prefill 战线会静默消失 —— 这正是这次"800 多被回滚"的观感来源。

---

## 3 新实测：chunk 32768 在 64K 上更慢（A 级）

生产 chunk 从 `auto:16384` 改 `auto:32768`，重启（250 s），同 seed 口径、`0 reused`：

```
prefill rep1  ttft 80.156 s  prompt_tokens 60201
prefill rep2  ttft 80.444 s  prompt_tokens 60254
PREFILL ttft median 80.300 s  CV 0.2%  (~750 tok/s)
```

| chunk | 64K TTFT | 吞吐 | 相对 16384 |
|---|---|---|---|
| 8192 | 81.0–81.5 s | 752 | −6.2% |
| **16384** | **75.1 s** | **801** | — |
| 32768 | 80.3 s | 750 | **−6.4%** |

⇒ **倒 U 的顶点在 16384 附近，两侧都掉 6%**；`W932` 只在 32K 长度上测过 32768（慢 1.9%），本轮补上 64K 档的 A 级证据。chunk 方向到此为止，除非 R72 扩 cache 改变约束（32768 借 4667 槽 = 62.5% cache，这是它变慢的一个候选原因）。

---

## 4 外证：同卡别人的 prefill 从那来（已核，不重复造轮子）

`milpster/gfx906-llama-cpp`（Radeon VII/MI50，llama.cpp fork，2026-09-24 同步）：
- PP16384 **439.6 vs 320.0 t/s（+37%）**、120k fill 280.7 vs 241.1（+16%）；27B Q6_K 双卡，非我们形状。
- 它自述的 prefill 主项是 **wave64 kernel tables**（上游 **#27841**，GCN per-arch MMQ config：nthreads 512 / 8 warps、J 到 128、MoE 保 J≤64）。
- **#27841 已在我们的 pin 里**：`~/strata166/llama.cpp/ggml/src/ggml-cuda/mmq-config-gcn.cuh` 有 `CASE(GGML_TYPE_Q4_K, 256/512, 2, 64/128, ...)` 全套 ⇒ 这一项**不是缺口**。
- 它另说「MMQ inner-loop restructures, 5 variants」全部失败、**~41% issue ceiling 是 gfx906 结构性的** —— 与 `W924` 的段计数（无段过半）、`W904` 的"解包 hoist 变慢 6–10%"互相印证：**改内层循环不是路**。

⇒ 结论一致：prefill 再往上，只能从**供给率（stream-k / 占用率）**或**算法（int8 attention / dot8）**取，不能靠重排内层。

---

## 5 R61 工具门：`rocprofv3` 当启动器可以，`HSA_TOOLS_LIB` 注入不行（B 级，已实测）

`W923` 三次注入全部空输出，结论是"工具不可用"。本轮把路径换掉：

```
rocprofv3 --pmc VALUBusy --output-format csv -d /tmp/pmcout -- ./stream_roof_w941 32 2
→ RC=0，输出 9_counter_collection.csv，VALUBusy 有值（read_kernel 5.97–7.93）
```

- **启动器路径可用**（rocprofv3 自己 exec 目标，注入由它完成）；
- `HSA_TOOLS_LIB` 那条路仍然不可用（`W923` 结论不变，只对"注入"成立）。
- 第一次尝试 `rocprofv3 ... -- python3 serve/server.py` **无数据**：引擎是 python 的子进程，注入没传下去。
- 第二次改成 **config.exe → wrapper**（`exec rocprofv3 … -- /data/bin/strata-0.1.56 "$@"`），让 rocprofv3 直接 exec 引擎 —— 结果见 §6。

---

## 6 生产形状 PMC（16K，`0 reused`）：注入生效，但**没能落盘** —— R61 仍未结

三次尝试，同一个 16K 档（每次全新 seed ⇒ 日志均 `0 reused`）：

| 次 | 做法 | prefill | rocprof 活动证据 | 输出 |
|---|---|---|---|---|
| 1 | `rocprofv3 … -- python3 serve/server.py` | 704.4 tok/s（15,734 tok） | 无（引擎是 python 的子进程，未继承注入） | **空** |
| 2 | config.exe → wrapper `exec rocprofv3 … -- /data/bin/strata-0.1.56 "$@"` | 714.4 tok/s（15,700 tok） | **有**：引擎日志里出现 `queue_controller.cpp:170 [queue-intercept] … falling back to system-memory ring` | **空**（`docker stop` 默认 10 s，强杀） |
| 3 | 同 2 + `docker stop -t 300`（走 server.py 的 SIGTERM→QUIT 路径） | 711.4 tok/s（15,819 tok） | 有 | **空** |

- **结论 1（B 级，已证）**：`rocprofv3` 作为**启动器**可以在这套自建 gfx906 包里工作（stream_roof 拿到 VALUBusy；引擎进程里出现 queue-intercept 行）。`W923` 判"工具不可用"只对 `HSA_TOOLS_LIB` 注入成立，本轮把它限定清楚了。
- **结论 2（B 级，已证）**：**输出落盘失败**。`-d /data/w941pmc` 目录三次全空，而 `/data` 是 bind mount（不是路径写错）。最可能的原因：rocprofv3 是 `popen` 的子进程、引擎是它的子进程，容器停止时整棵树被回收，tool 的 finalization 没跑完。
- **副产品（A 级，有用）**：**开 PMC 后 prefill 只慢 1–6%**（711–714 vs 759 @16K，含观察者开销）⇒ PMC 采集本身可承受，值得继续，不是"一开就废"。
- **下一步（唯一确定的路）**：rocprofv3 **直接 exec 一个会自然退出的独立可执行**（stream_roof 就是这样成功的）。MMQ 的现成驱动是 `tests/cuda/prefill_mmq_kquant_test.cpp` / `prefill_mmq_tab_test.cu`（CMake target 已有，`build-r28` 未开 `BUILD_TESTING`，需手抽编译行）。这就是 `W939 §2` 给 R61 定的"独立进程"路线，本轮把它的**工具门**打通了，只差驱动。

---

## 7 生产快照（本轮结束时，8 字段见汇报）

| 项 | 值 |
|---|---|
| 容器 / 镜像 | `4f387a12e84b` / `strata-gfx906:0.2.10-101`（image `5267df6dbdeb`） |
| 引擎 | `ae085365441381c438b56bcabcccf450`，42,924,432 B，`strata 0.1.56` |
| disk = build = running | **三方一致**（`ae085365…`） |
| config | `24d66f6a86d7b75f58015efa38d462d2`，`exe=/data/bin/strata-0.1.56` |
| 健康 | `/health ok`，`StartedAt 05:57:18Z`（重启后加载 232–250 s） |
| 资源隔离 | `ulimit -l = unlimited`、`VmLck 28,125,140 kB` |
| 显存 | `expert cache 7463 slots / 21.79 GiB`、`borrows 2606 slots (7.62 GiB)`、`VRAM free 882 MiB` |
| 本轮改动 | **零**（chunk 32768 实验后已恢复 `auto:16384`，config md5 与 `bak_w941` 一致） |

回滚：`docker exec strata166-407 cp /data/strata-huihui-ud-iq4_xs.json.bak_w941 /data/strata-huihui-ud-iq4_xs.json && docker restart strata166-407`

---

## 8 R85 的主攻方向：不是 MMQ，是 **attention 效率**

按 `W832 §6.5` 的相位表与 `W887`：

| 阶段（长档 prefill） | 占比 | 现状 | 可动空间 |
|---|---|---|---|
| MMQ（gate/up + down） | 34.6% | 供给率 4.55 / 21.52 TMAC/s = **21%**，但 MMQ 相位内已 50–65%（`W923` 算术）；外证「41% issue ceiling 是结构性的」 | stream-k 待 PMC 判；dot8 上限 3.22% |
| **QSA attention（99K）** | **19.2%** | 有效算力 **1.5–2.1 TFLOPS = FP32 峰 13.4 的 11–16%**（`W887`） | **修效率到 50% 峰 ⇒ −13.4% 端到端**（`R46`） |
| GDN | 6.2–9.6% | 已拆 8 段计时，11.64 ms/窗口 | `R54` 已判否（T≥4 才赢） |
| wait copy / dequant | 8.9–12.7% / 9.5% | chunk 越大越摊薄 | 已被 chunk 16384 吃掉一部分 |

⇒ **R85 的第一手段是 R46（attention 效率，`Castagna fattn-qsa-gcn` 路线：不建 [n_kv,T] mask、48 行/块、64-cell 分段）**，第二是 R64（Q·K int8），第三才是 R60。

⚠️ **口径必须写清，否则会重犯 R64 的错**：`W887` 的 13.4% 是"把 attn 相位从 11–16% 峰提到 50% 峰"；`W926` 只算点积那一段，得 3.40/4.25/5.95%（且 V 是 4-bit，`v_dot4` 吃不上）。两者不矛盾但**不可混用**：R46 的第一步必须是**把 attn 内部拆成 反量化 / 点积 / 写回 三段**（一次重建录 `STRATA_QSA_DUMP`），再谈能拿哪一段。`R64` 已经证明"只看占比就动码"会得到 C 级结论。

`tests/cuda/pa_bench.cpp` 是 attention 的现成探针 ⇒ 与 R61 的独立可执行路线可以合并到同一次构建里做。

---

## 9 顺手审计出的一处账本不一致（**未改，留待决策**）

`W938 §163` 写「`ci/config.sh` 已改为 `BUILD=build-r28`、`IMG=strata-gfx906:0.2.10-101`」，但本轮实测磁盘上仍是：

```
BUILD=/home/albus/strata166/gfx029-build     # 0.1.55 的旧构建目录
IMG=strata-gfx906:0.2.9-101
```

- 影响：下一次 `strata-ci build/deploy` 会拿 **0.2.9 镜像 + 旧构建目录**，与生产（0.2.10-101 / build-r28）不是同一套 —— 这正是 `W937` 修的"账本失真"的另一个入口。
- 没动的原因：改它会产生新 commit，而 `R80` 的 provenance 检查要求「末条 tag == HEAD tag」，当前 HEAD 就是 `mi50-0.2.10-r28` ⇒ 要么改完补一个 tag，要么把这条并进下一次 tag。**下一轮先处理它，再动任何构建。**

---

**【AUDIT24 口径注记】**
**每秒口径**：§1 的「801.4 tok/s」应写日志原值 —— `60330 / 75030 ms = 804.1`、`60008 / 74987 ms = 800.2`，中位 **802.2**（CV 0.085%）。801.4 是早一版草稿的笔误，不影响任何结论。
