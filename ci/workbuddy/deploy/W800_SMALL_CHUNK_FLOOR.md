# W800 多轮地板的真身：不是 park，是「小于 1024 token 的 chunk」

- 日期：2026-10-25 20:57-22:20
- 起点：`W799` 把多轮的固定成本记为「每轮约 900 ms，其中约 450 ms 是 park/unpark」，处置为 PENDING。
- 本轮结论：**W799 的归因错了一半。** park 不在客户端关键路径上；地板是**小 chunk 的 prefill 本身**，由三个「按专家计费」的相位构成。
  参数面 `STRATA_PREFILL_STREAM_MIN` 试过、**否决**（小 chunk 反而慢 2.4 倍）；另**采纳 1 项**：
  `STRATA_ROUTE_TAIL_SKIP=7` 由「宏泄漏导致的隐式默认」改为**显式写死**（实测 +6.5% decode），产出一个 P0 正确性发现（P127）。
- 未改动生产：`0.2.4p4` / env 10 项 / `verify_config` PASS=34 FAIL=0 / `gen_config --live` 无差异。


> **【W805 更正 2026-10-26 19:5x】后半句已过时。** 现在的日志里有 **283 条** `conversation cache: restored N tokens (checkpoint) in X ms`（对照 3,176 条 `parked`），最近 40 次的等效速度是 **89,510 tokens / 2,043.8 ms = 43,796 tok/s**（重读同一段在 640 tok/s 量级 ⇒ 快 68 倍）；checkpoint 的保存成本中位 **74.2 ms**（n=135），所以一次 restore 只要恢复 >48 个 token 就回本。⇒ 会话缓存的 restore 路径**在这个构建上是工作的**（`issue #4081` 的「只 park 不 restore」至少已被修好），「resume 只来自热批槽」这个结论作废。详见 `W805 §6`。
---

## 1 先修工具：拿到逐阶段的时间线

W799 只有 /metrics 的 `prompt_ms` 一个数。本轮把引擎自带的两层诊断同时打开，并解决了它们的取证问题：

| 开关 | 输出 | 用处 |
|---|---|---|
| `STRATA_TRACE=1` | `strata trace: request/prompt start/lent N slots/read N tokens (batched) in X ms/checkpoint at/refill/window` | 请求内分段 |
| `STRATA_PREFILL_TIMING=1` | `strata prefill timing: N tokens, GPU timeline X ms, wall Y ms, host staging Z ms: 21 相位` | chunk 内相位 |

**取证陷阱（记下来，避免下次白跑）**：这些行**不进 docker logs**。`serve/server.py:1021` 只把 `progress_at` 那几行（`[strata] reading the prompt…`）回显到容器 stdout，引擎 stderr 落在
`/home/albus/strata166/data/strata-huihui-ud-iq4_xs.log`（`/data` 是宿主挂载）。
⇒ 所有逐阶段证据都从那个文件 `grep`，`docker logs` 里永远看不到 `strata trace`。

---

## 2 一个多轮请求到底花在哪（3 轮，read=211/223/235）

引擎逐字（`--conversation-cache-park-gain` 未设，即默认 0）：

```
strata trace: request 7788 0
strata trace: prompt start 7787 -1
strata trace: lent 192 slots for 256 tokens in 0.1 ms
strata trace: prompt chunk 0 of 206
strata trace: read 206 tokens (batched) in 1888.2 ms          <- 86% 在这里
strata trace: checkpoint at 7783: sync 0.0 ms, save 80.2 ms
strata trace: refill start 192 -1
strata trace: refilled 192 slots on 1 stage(s) in 36.6 ms
strata trace: read 4 tokens (windows) in 52.7 ms
strata trace: prompt done (slots refilled) -1 -1
strata trace: window ...（4 行，decode）
strata serve: conversation cache: parked 7795 tokens in 262.4 ms ... reused_kv_bytes=0
```

对账（/metrics 同请求：`prompt_ms=2226.2 decode_ms=183.2`，客户端 wall=**2.423 s**）：

| 段 | ms | 占 wall |
|---|---|---|
| read 206 token（batched） | **1888** | **78%** |
| checkpoint save | 80 | 3.3% |
| refill lent slots | 37 | 1.5% |
| read 4 token（windows） | 53 | 2.2% |
| 未归因（admission/句柄） | ~155 | 6.4% |
| decode（/metrics） | 183 | 7.6% |
| **合计** | **2396** | 99% |

**park 的 262 ms 不在 t0..t1 里**（2226+183=2409 ≈ wall 2423-14）。三轮都是如此。
⇒ **park 发生在响应交付之后**，不占客户端延迟。W799 里 `gain=256` 让中段 read 掉 10%，不是"省掉了 park 的延迟"，
而是 park 线程与下一请求争 CPU/RAM（推断，未单独验证）；P126 的处置理由要按这条改写。

`reused_kv_bytes=0` 也解释清了：resume 来自**热批槽**（`lent 192 slots`，日志里没有任何 `restored N tokens` 行），
不走会话缓存 ⇒ `retain()` 从未被调用。上游 `PR #4002` 逐字确认另一半："`unchanged_tokens` remains zero,
**so every save copies the complete image**"。**这是设计，不是 bug**；真正的 bug 是 `issue #4081`。

---

## 3 地板在 read 里面：一个 1024 token 的断层

同一会话、只变 read 长度（生产配置，`--prefill auto`，读入即一个 chunk）。`wait copy` 是 prompt 路等 H2D 专家拷贝的相位。

| tokens | wall ms | **wait copy** | dequant | gemm g/u | gemm down | hc read | host staging | qsa attn |
|---|---|---|---|---|---|---|---|---|
| 120 | 1313 | **301** (22.9%) | 221 | 286 | 149 | 107 | 180 | 36 |
| 226 | 1984 | **479** (24.1%) | 276 | 615 | 203 | 113 | 216 | 67 |
| 424 | 2402 | **613** (25.5%) | 336 | 580 | 287 | 126 | 261 | 127 |
| 810 | 3220 | **754** (23.5%) | 380 | 782 | 378 | 175 | 343 | 241 |
| 834 | 3432 | **791** (23.1%) | 415 | 810 | 420 | 184 | 320 | 248 |
| 1588 | 3733 | **57** (1.5%) | 534 | 1025 | 489 | 266 | 480 | 481 |
| 2988 | 5405 | **36** (0.7%) | 521 | 1371 | 651 | 387 | 413 | 889 |
| 7577 | 10731 | **28** (0.3%) | 462 | 2500 | 1196 | 895 | 155 | 1952 |

（120/226/424/810/1588/2988/7577 取自同一次递增扫描；140/250/465/834 取自 A 臂 rep1，同配置。
两次在相近尺寸上互差 <4%，趋势一致。）

**断层在 810 与 1588 之间。** 源码给了解释（`prefill.cpp:178`、`2875`）：

```cpp
constexpr int64_t kStreamAllMinDefault = 1024;   // 2026-10-25 实测：1024 是上游在*独显*上量出来的下限
const bool stream_all = m.ring > STAGE && T >= stream_all_min() && m.src != nullptr;
// 「Step 3: from this chunk size on, every non-resident expert of every layer streams in a fixed order
//   through a ring_slots()-slot ring (nearly all 512 are routed at such a chunk), so the copy engine keeps
//   working through the attention halves instead of waiting for each layer's routing.」
```

即：**T < 1024 时走 routed-only 8 槽环**（`constexpr int STAGE = 8`），拷贝跟着每一层的路由走、无跨层流水 ⇒ `wait copy` 暴露；
T >= 1024 走全流式大环 ⇒ 拷贝被 attention/GEMM 盖住，`wait copy` 掉到 1% 以下。

**这条断层正好落在真实用法上**：多轮 / agent 的一轮提示就是 100-1000 token。

---

## 4 试过并否决：`STRATA_PREFILL_STREAM_MIN`

思路：把小 chunk 也塞进全流式路径，让拷贝被流水盖住。三臂（A=默认 1024 / B=128 / C=64，各 1 次全量扫描；
因为测试尺寸全部 >128，B 与 C 等价，实为两臂）。

| read | A(1024) prompt_ms | B(128) | 差 | C(64) | 差 |
|---|---|---|---|---|---|
| 145 | **1851** | 3859 | **+108%** | 4037 | +118% |
| 255 | **2262** | 3882 | **+72%** | 3869 | +71% |
| 470 | **3219** | 4010 | **+25%** | 3921 | +22% |
| 839 | 4078 | **3913** | **-4.0%** | 3954 | -3.0% |
| 2993 | 6070 | 6108 | +0.6% | 6089 | +0.3% |

相位证据（同一 chunk 的 `wait copy`）：140 token 334→**1974**；250 492→**1686**；465 652→**1276**；834 791→661。

**机理**：全流式是「每个非驻留专家按固定顺序过一遍」——对 7577 token 的 chunk，512 个专家被 7577 个 token 共用，
分摊后几乎免费；对 140 token 的 chunk，**它把 512 个专家全部搬进来，而每个专家只服务 0.3 个 token**。
上游 `docs/STRIX_HALO.md:121-131` 逐字就是这个意思：

> `STRATA_PF_FUSED=1` reaches only chunks of `STRATA_PREFILL_STREAM_MIN` tokens or more (1,024 by default,
> **the floor measured on a discrete card, where a smaller chunk does not pay for streaming every expert**)
> … an agent's turn … read in 3.1-6.0 s at 1,024 and 0.9-2.5 s at 128 (…) 12-turn replay 3.4 -> 2.1 s per turn

那段「3.4→2.1 s/turn」是 **Strix Halo（统一内存，什么都不用搬）** 的战绩，**不能外推到独显**。我们的 A/B 复现了
「独显上小 chunk 不划算」这半句，并且量出了幅度：**+72% ~ +108%**。

⇒ **P128 记 REJECTED（`STRATA_PREFILL_STREAM_MIN` 不采纳，默认 1024 是对的）**。
唯一可记的边角：839 token 时 B 快 4.0% —— 说明 1024 这个门槛在 800-1000 区间略保守，但收益 <5% 且只影响窄带，不动。

---

## 5 机制级结论：拷贝带宽已经满速，pin/resident 一族**不可能**救 wait copy

W799 之后的直觉是「拷贝慢 ⇒ 钉住宿主内存」。本轮用一个 40 行 HIP 探针直接量（`albus/r5/pcie_probe.cpp`，
gfx906 / ROCm 7.14 / 4 MB × 50 次，每次同步）：

| 源 | 4 MB/次 | 带宽 | 2.79 MB/次 | 带宽 |
|---|---|---|---|---|
| pageable（`std::vector`） | 346.2 µs | **12.11 GB/s** | 225.0 µs | 13.00 GB/s |
| pageable，批量不逐次同步 | 330.5 µs | 12.69 GB/s | — | — |
| pinned（`hipHostMalloc`） | 312.9 µs | **13.40 GB/s** | 220.5 µs | 13.27 GB/s |
| file-backed mmap | 318.6 µs | 13.16 GB/s | — | — |

三条：
1. **pageable ≈ pinned（只差 10%）**，file mmap 也同样是 13 GB/s ⇒ 在这台机器上"钉页"几乎没有收益。
2. 2.79 MB / 225 µs 与上游 `PR #4005` 的 Linux 实测（registered 205 µs）同档，说明探针口径对得上。
3. 反推拷贝量：`host staging`（issuer 线程被拷贝占住的时间）= 180/216/261/343 ms for 140/226/424/810 token
   ⇒ ×13 GB/s = **2.3/2.8/3.4/4.5 GB**，即 **约 580-1100 个 4 MB 专家拷贝**。
   这些专家在 40% 驻留（9901/24576）的缓存下必然要过 PCIe，**带宽已是上限，只能减少字节数**。

⇒ 直接关掉一整族假说：`--resident-experts` / `--resident-cpu-experts` / `STRATA_RESIDENT_PIN`
（P09 作废、P66 REJECTED、P71 CANDIDATE）**在机制上救不了 wait copy**，因为它们的卖点是"钉住的 RAM 拷贝更快"，
而本机 pageable 已经 12.1 GB/s。P66 当年"prompt 不减"的实测，到这里有了机理解释，不必再跑。

---

## 6 P0 正确性发现：`STRATA_USE_HIP` 宏缺失 ⇒ CUDA 专属默认在 gfx906 上生效

引擎启动横幅（生产配置、env 只有 10 项、**没有** `STRATA_ROUTE_TAIL_SKIP`）：

```
strata serve: STRATA_ROUTE_TAIL_SKIP=7 is ON (default): a missed expert that every token of a verify window
routes at rank 7 or lower is skipped (+10..20% decode on 12-16 GB cards that miss experts;
answers differ slightly from 0.1.41); STRATA_ROUTE_TAIL_SKIP=0 turns it off

strata serve: route tail skip: 1113 missed experts skipped (1201 entries) since the start
strata serve: route tail skip: 1292 missed experts skipped (1390 entries) since the start
```

来源（`generate.cpp:1941`）：

```cpp
static bool decode_defaults_arch_ok() {
#if defined(STRATA_USE_HIP)
    … return gfx_arch_is_gfx12_wmma(p.gcnArchName);
#else
    return true;                       // ← 本机构建走这条
#endif
}
```

本机构建只定义 `STRATA_HIP_GFX906`、**不定义** `STRATA_USE_HIP`（P23 早已在 `compile_commands.json` 里查实：
`STRATA_USE_HIP` 计数=0，`-DSTRATA_HIP_GFX906` 26 处），于是走 **CUDA 分支 `return true`**。
`generate.cpp:9866` 用它做 `tail_default_ok` 的唯一架构门 ⇒ **ROUTE_TAIL_SKIP=7 在 gfx906 上默认开启**。

三条后果：
1. 上游注释与文档都说这项「ON BY DEFAULT on CUDA builds **and on HIP gfx1200/gfx1201**」——**gfx906 不在名单里**，
   我们却一直在跑；它按设计**改变答案**（上游口径：KL 0.003-0.006，量级与量化误差相当）。
2. 今天所有基线（含 decode 683-695 tok/s）都含它，横向可比，但**与"纯 0.1.41 数值"不可比**。
3. **最大的风险是将来**：若上游修好 `STRATA_USE_HIP`（或我们重建时补上宏），这项会**静默变回关**，
   decode 掉的幅度无人认领。同理 `arm_cpu_share()` 的 `#if !defined(STRATA_USE_HIP)`（P23）也是同一根因。

**处置建议（待做）**：把 `STRATA_ROUTE_TAIL_SKIP=7` **显式写进 config env**（钉住行为，与 P23 把
`STRATA_PREFILL_CPU_SHARE=0` 显式写死是同一纪律），并单开一轮量出它在本卡的真实 decode 增量与 KL。

**系统性挂账（W801）**：`generate.cpp` 里 `STRATA_USE_HIP` 共 33 处，其中 7 处用
`(defined(STRATA_USE_HIP) || defined(STRATA_HIP_GFX906))` 的合并写法 —— 说明"gfx906 是另一种构建"是上游已知形态，
但**凡是只写 `STRATA_USE_HIP` 且用于决定"默认值"的站点都会在本机构建上走错分支**。已确认成员：`decode_defaults_arch_ok()`
（→ ROUTE_TAIL_SKIP）、`arm_cpu_share()`（→ P23）。其余 31 处需按「是否决定默认值 / 还是只选内核」逐条分类。

### 6.1 A/B：它到底买了多少（ON=7 vs OFF=0，交错 3 次，6 臂）

2K 会话、每轮生成 96 token、`temperature 0`，同一提示词逐轮配对。**两臂内部方差极小，区间不重叠**。

| turn | ON=7 decode_ms（3 次） | OFF=0 decode_ms（3 次） | 差 |
|---|---|---|---|
| T0 | 2070.7 / 2022.2 / 2018.1（均 2037.0） | 2209.1 / 2210.0 / 2239.9（均 2219.7） | **-8.2%** |
| T1 | 1851.3 / 1858.8 / 1860.1（均 1856.7） | 1868.5 / 1864.9 / 1847.1（均 1860.2） | -0.2% |
| T2 | 1600.2 / 1613.9 / 1608.1（均 1607.4） | 1790.7 / 1795.9 / 1829.7（均 1805.4） | **-11.0%** |
| 合计 | **5501.1** | **5885.3** | **-6.5%** |

- `--spec 4` 的草稿：ON 51/66、51/58、54/57；OFF 48/56、50/61、49/56 ⇒ **skip 反而多给草稿**，与上游 #1884
  「skip 压低接受率」的说法相反（我们是 32 GB、缺专家 60%，和它的 94.8% 驻留场景不同）。
- **未解释的观察（不作证据）**：`prompt_ms` 也同步偏低（T0 中位 651 vs 744、T1 772 vs 820、T2 859 vs 1025，-6% ~ -16%）。
  该开关只作用于 verify window，机理不明；列在此处仅供后续追查，**不参与本条采纳判断**。
- **结论：留 ON，并显式写死 `STRATA_ROUTE_TAIL_SKIP=7`**（P127）。它原来靠宏泄漏"免费"生效，
  哪天上游补上宏就会无声消失、白掉 6.5%。
- **代价必须记着**：它按设计改答案（上游口径 KL 0.003-0.006，与 IQ4_XS 量化误差同量级）。
  正确性门（`STRATA_LOGPOS` teacher-forced KL，self 对照）**尚未做**，列为 W801 首项。

---

## 7 这一轮改变了什么判断

1. **多轮的瓶颈不是"搬 KV"，是"搬专家"**。KV snapshot 的 park 200-300 ms 在响应之后，不在延迟里；
   真正吃时间的是那 2.3-4.5 GB 的专家拷贝 + 它们的 dequant + 逐专家 GEMM。
2. **小 chunk 有结构性下限**：一个 140 token 的 chunk 与一个 7577 token 的 chunk **要搬的专家数量是同一量级**
   （580 vs 513 个拷贝），所以前者的"每 token 成本"天然高一个数量级。这不是调参能解决的，
   只能靠 (a)更多 VRAM 专家缓存 (b)稀有专家交给 CPU (c)让 chunk 变大。
3. **今天所有 prefill 优化（-30.6%）对小 chunk 的收益被摊薄**：那些优化缩短的是 `gemm/attn` 里与 token 成正比的部分，
   而小 chunk 里 47% 是 `wait copy + dequant`（与专家数量成正比、与 token 无关）。
4. **pin/resident 一族正式关闭**（机制级，不再需要 A/B）。
5. **一个 P0 正确性洞**：CUDA 专属默认经宏泄漏到 gfx906；实测 ROUTE_TAIL_SKIP 给 **+6.5% decode**，
   已显式写死（P127，env 10→11 项），但它的 KL 代价还没过门。

---

## 8 下一轮（按收益排序）

1. **`STRATA_PREFILL_STREAM_MIN` 已关**；改攻"减少被触碰的非驻留专家"：
   - `STRATA_PREFILL_CPU_SHARE`（P23 只在 **T=4** 测过，那是 launch-bound 区，不能外推到 200-800）；
     在本轮区间重测，判 `wait copy` 是否下降。
   - VRAM 专家缓存从 9901 往上加的唯一路径是**腾 VRAM**：`--vram-reserve-mib` 现在是 768，而引擎在新 env 组合下
     报 `only 506 MiB of VRAM free … add --vram-reserve-mib 832`（§9），说明**缓存已经挤到安全线以下**，方向相反。
2. **W801 宏泄漏审计**（33 处 `STRATA_USE_HIP`，只找"决定默认值"的站点）。
3. **ROUTE_TAIL_SKIP 已定量并显式钉住**（P127，+6.5% decode）；剩 KL 门与「其余 31 处宏站点」的审计。
4. 多轮的**唯一还有把握的减法**：`--prompt-cache-every` 相关的每轮 checkpoint save（65-100 ms）与 refill（37-218 ms）。
5. 内核工程（MMQ 36.4% / attn 19%）仍挂 —— 但在小 chunk 里它们只占 21%/3%，优先级继续下降。

---

## 9 生产状态与一条新告警

- `strata166-407` / `strata-gfx906:0.2.4p4` / 0.1.49.2 / **env 11 项**（本轮 +`STRATA_ROUTE_TAIL_SKIP=7`）/ 驻留专家=**9901** /
  `verify_config` **PASS=35 FAIL=0** / `gen_config --live` **无差异**。
- 新增告警（引擎逐字，本轮第一次出现）：
  `WARNING: only 506 MiB of VRAM free at the start of this request (below 512 MiB) … Add --vram-reserve-mib 832`。
  ⇒ 现役 `--vram-reserve-mib 768`（P62 采纳值）在今天的 env 组合下**低于引擎自己的安全线**；#2065 的后果是
  decode 掉到个位数 tok/s。待定：升到 832（专家缓存少 64 MiB）还是降 max-context。

## 10 复现脚本（`albus/r5/`）

| 文件 | 作用 |
|---|---|
| `mt_scan.py` | 同会话递增 read（120/230/430/810/3098）取 prompt_ms + 相位 |
| `mt_trace.py` | 3 轮固定会话，客户端打点 T0/T1 与服务端 trace 对齐 |
| `ab_p10.sh` / `w800_setenv.py` | `STRATA_PREFILL_STREAM_MIN` 三臂 |
| `ab_p11.sh` / `w800_setts.py` / `mt_dec.py` | `STRATA_ROUTE_TAIL_SKIP` 7 vs 0，decode 96 token |
| `pcie_probe.cpp` | H2D 带宽：pageable / pinned / file-mmap |
| `_rsh.py` | 166 通道（ssh + base64 脚本，避开 argv 8000 字节截断） |
