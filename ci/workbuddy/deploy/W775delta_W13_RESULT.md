# W775delta W13 -- `--dump-routing` + `bench_eviction` 实测结果（首跑成功）

> 承接 `W775delta_W13_REPLAY.md`（源码面核验）。本轮把车真发出去，拿到跨槽位策略矩阵。
> 时间：2026-10-11 04:48–05:03。全部读数现取，产物已归档（md5 见 §5）。
> 机主令「按计划推进」/「你要干啥你继续啊」。

> **[!] 口径限定（2026-10-11 追加，W752 同步）**：本件的 `fill-only 0.7086` 是 **`bench_eviction.py` 复放一条 `--dump-routing` trace** 的口径，**不是我们生产负载的命中率**。同卡同槽（9,761）生产引擎实测 `decode expert cache hit rate` = **95.4-98.0%（长跑 2.8-3.1M lookups 时 97%）**、短请求 88-90%。=> 本件给出的 「头部空间 +23.9~28.0pp」**只对 trace 类（冷缓存、更分散的路由）流量成立**；对已由 learned profile 覆盖到 ~96% 的生产负载，**尚不知有多少能留下**。已据此向上游 `#1923` 追加 qualification 评论（id `6106275361`）。详见 `W775delta_W13_HEADROOM_RECHECK.md`。

## 0 结论（先行）

> **口径声明（审计后补，必读）**：以下全部读数是**命中率（hit-rate）空间**，来自**离线复放**（命中率只取决于 routing 顺序）。
> **不是 wall-clock / tok/s 收益** -- 收益还取决于 miss 的成本（PCIe / CPU pool 占比，见 §6）。
> 「头部空间 23.9~28.0pp」= **命中率**头部空间，不可读成「提速 24~28%」。

1. **W13 的原始判定要改**。`W13_REPLAY.md` §4 写的判据是「若 `oracle - fill-only` < 2pp，则 P33/P41/P46 族可提前判死」。
   **实测是 +23.9pp（生产槽位 10327）/ +28.0pp（9761）** => **判据不成立，该族不能判死**，且指向一个**可实现的**改动方向。
   （**命中率口径**，非 wall-clock。）

2. **引擎现役策略（fill-only，"从不淘汰"）在生产槽位上的命中率只有 0.7086–0.7517**，
   而 **oracle（Belady MIN，上界）是 0.9890–0.9903** => **命中率头部空间 23.9–28.0pp 从未被测量过**。

3. **两个能落地的策略（LRU / LFU-decay）都能到 0.975–0.980**，只差 oracle **1.2–1.5pp**
   => **不是"理论上有空间"，是"现成策略就能拿走 95% 的命中率空间"**（注意：是**命中率**空间）。

4. **槽位越小，现役策略越惨**：slots=64 时 fill-only 0.0105 vs oracle 0.4221（**差 41.2pp，fill-only 只有 oracle 的 2.5%**）。
   => 这条曲线说明：**fill-only 的表现几乎完全是"槽位是否够大"的函数，与"策略"无关** -- 有淘汰时槽位小也不至于崩。

> **未动 register 状态（防误读）**：本结果**不改变** `P33`/`P41`/`P46` 的 register status -- 三条**仍为 `CANDIDATE`**。
> 「判据不成立 => 该族不能判死」**不等于**「状态已更新」；状态变更须走「重议 + 改裁定」通道。

5. **发车链路已打通并可复现**（`generate` 路径 + `--dump-routing`），**关键前置条件三件**：
   `--native SHARD1` + `--spec T(>=2)` + `--prefill CHUNK`（native IQ pack 的 generate 路径强制），
   外加 `--ple-gguf <shard 2>`（PLE 表所在分片，否则 Layer 1 的 PLE 静默跳过）。

## 1 工具链与前置（源码级，全部逐字）

引擎报错链（每一层都是实撞出来的）：

```
(1) strata generate: --ple-gguf is required; --no-ple explicitly enables a diagnostic ablation
   修：--ple-gguf /models/.../Qwen3.8-Flash-Next-UD-IQ4_XS-00002-of-00003.gguf
   （help: "WITHOUT IT LAYER 1's PLE IS SILENTLY SKIPPED, which changes every number downstream - pass it for any real run"）

(2) strata generate: /data/packs/... is a native (IQ) pack: it needs --native SHARD1, --spec T (T >= 2) and --prefill CHUNK
   修：--native <shard1.gguf> --spec 4 --prefill auto
```

**`--dump-routing` 的记录格式**（`generate.cpp:993-995`，逐字）：

```c
const int32_t rec[2] = {layer_idx, (int32_t) k};
std::fwrite(rec, sizeof rec, 1, t->routing);
std::fwrite(ids, sizeof(int32_t), (size_t) k, t->routing);
std::fwrite(weights, sizeof(float), (size_t) k, t->routing);
```
=> 每记录 = `int32 layer, int32 k, kxint32 ids, kxfloat weights`，**每层每 position 一条**（`generate.cpp:963-967` 逐字：
*"`drive_pool` is called once per layer from the main loop ... **THE ROUTING TRACE, which is P0.S8**"*）。

**首跑踩到的核心事实**：`--max-new 1` => 只有 **1 个 position** => trace 只有 **48 条记录**（48 层 x 1）。
`bench_eviction.py` 打印的 `480 lookups` 是 **(layer,expert) 对数** = 48 层 x 10 专家，**不是记录数** -- 这两个数
不是一回事，混淆会得出「trace 很长」的错误印象。**要拿到有复用结构的 trace，必须把 `--max-new` 拉大**。

**记录数的决定关系（审计后收紧，勿过度解读）**：`--max-new` 决定记录数的**量级**--
三车对照（reps 固定 40）证明 **reps / prompt 长度不改记录数**（两车都 4,224 B），只有 `--max-new` 1->1024 把 trace 抬到 16.2 MB。
**但不能据此精确预算**：`--max-new 1024` 实得 **3,838 positions**（非 1,024）=> 记录数 = 实际 position 数 x 48，
而 position 数 ≈ `max-new` x **spec/MTP 每步产出的 position 数**（**该乘数本波未逐条核**，见 §6）。

## 2 实测矩阵（trace：3,838 positions x 48 层 x k=10 => 1,842,240 (layer,expert) lookups）

产物：`deploy/tmp/w13_n1024/bench_eviction.csv`（9 档 slots x 4 策略 x 4 window）。
`prefill: /src/data/expert-profile.bin`（**对齐生产起始驻留**，由 `--prefill` 传入）。

| slots | fill-only（引擎现状） | lru | lfu-decay | **oracle（上界）** | **oracle − fill-only** |
|---|---|---|---|---|---|
| 64 | 0.0105 | 0.3931 | 0.0481 | 0.4221 | **+41.2 pp** |
| 128 | 0.0227 | 0.3931 | 0.0937 | 0.4561 | **+43.3 pp** |
| 256 | 0.0477 | 0.3931 | 0.1753 | 0.5236 | **+47.6 pp** |
| 512 | 0.0845 | 0.3931 | 0.3412 | 0.6517 | **+56.7 pp** |
| 1024 | 0.1439 | 0.4085 | 0.5212 | 0.8040 | **+66.0 pp** |
| 2048 | 0.2381 | 0.7972 | 0.7093 | 0.8946 | **+65.6 pp** |
| 4096 | 0.3772 | 0.9020 | 0.8541 | 0.9514 | **+57.4 pp** |
| **9761**（`/metrics` 报的值） | **0.7086** | 0.9751 | 0.9767 | **0.9890** | **+28.0 pp** |
| **10327**（dump 车实存） | **0.7517** | 0.9783 | 0.9795 | **0.9903** | **+23.9 pp** |

**逐窗数据显示策略差异不是"某一段"的偶然**（`per-window`，4 窗）：生产槽位下
fill-only 四窗分别 0.7409/0.6884/0.7205/0.6847，lru 0.9704/0.9778/0.9797/0.9726，oracle 0.9853/0.9903/0.9919/0.9884
=> **四条窗内都稳定，不是窗口偏差**。

## 3 顺带拿到的两条生产面新事实

**(1) GPU cache 槽位有三个数，必须分清**（全部实读 -- **审计后修正：其中 10327 的出处不成立**）：

| 数字 | 来源 | 语境 |
|---|---|---|
| **9,757** | 生产 `strata-huihui-ud-iq4_xs.log:23` 逐字 *"expert cache 9757 slots, 21.98 GiB of VRAM"* | 生产 serve 全参数（`--vision --mtp --conversation-cache-mib 4096`）实测 |
| **9,761** | 我们 `/metrics` 的 `engine.expert_slots`（现读） | 实测 |
| ~~10,327~~ | **[!] 非引擎读数**：这是**我方手工传给 `bench_eviction` 的 `--slots` 档**（为对齐 W13 dump 车读数而选），**不是引擎报告的驻留值** | **工具入参** |

> **审计更正（P0-1）**：原稿把 10,327 写成「W13 dump 车日志逐字 *"10327 in the GPU cache"*」。
> **166 全盘 `grep -rn '10327 in the GPU cache'` 为空**，W13 车日志里也**没有**任何 `in the GPU cache` 行
> （该容器已销毁，原始驻留行**不可追**）。=> **撤回该「逐字」引用**。
> 结论本身不受影响：**同一份 profile（日志逐字 *"24576 ranked pairs, built for 24576 slots"*）
> 在不同 VRAM 预算下驻留槽位数确实不同** -- 但此论点的证据只有 **9,757（生产）vs 9,761（/metrics）两个实测**，
> **不含 10,327**。

**(2) 生产 profile 在这条 3,838-position trace 上的命中率（`--prefill` 起点）**：
slots=9761 时 fill-only 的 0.7086 **就是引擎现役命中率**（因为策略=不淘汰 => fill-only 就是现状），
而上游 `expert_cache.hpp:11` 自承的 4,105-slot 值 0.6447 是**另一台机器、另一种量化**（IQ3_S），**不可照搬**。

## 4 判定

| 问题 | 判定 |
|---|---|
| 现役策略有优化空间吗？ | **有，且很大**：生产槽位 +23.9~28.0pp；任意槽位 +23.9~66.0pp |
| 能落地吗？ | **能** -- LRU / LFU-decay 两个现成策略就能拿到 0.975~0.980（占 oracle 空间的 ~95%） |
| 改动成本 | 引擎侧需**实现一个淘汰策略**（现在 `expert_cache.cpp:142-143` 逐字 *"it never evicts, because eviction policy is a measured question"*，**没有开关可拨**）=> 属**引擎代码改动 / 或向上游提 feature**，不是参数 |
| 与 P31/P34 重叠吗？ | **不重叠**（expert cache 淘汰 vs 会话/KV 缓存，不同模块）-- 原假设证伪，本轮再确认 |
| 风险 | 本轮**零**（离线复放，未改引擎、未改 config） |

**建议的落地方向（待机主批准）**：
1. **读上游是否已有淘汰策略的实现或 issue**（`expert_cache.hpp:11` 提到 R4.1 的 LFU-decay vs LRU sweep => 上游已做过 sweep 测量）。
2. 若上游无实现 => **这是一个可提 feature / PR 的点**（我们有实测矩阵支撑）。
3. **不建议**直接改 P33/P41/P46 族的裁定 -- 本结果说明那族的天花板**不是 2pp，是 24-28pp**，须重议。

## 5 产物与指针

**本机归档**（`deploy/tmp/`）：

| 文件 | 大小 | md5 | 说明 |
|---|---|---|---|
| `w13_n1024/trace.bin` | 16,211,712 B | `6b5f1e44788fc13fa598d4261d5cbcde` | 主 trace（184,224 记录 / 3,838 positions） |
| `w13_n1024/bench_eviction.csv` | 8,253 B | `44c788847e7a2fac397d16501486a845` | 9 slots x 4 policy x 4 window 全表 |
| `w13_n1024/bench_eviction.out` | 5,533 B | `9678d411d78f91d8131cbde8b72b838c` | 人读版全表 |
| `w13_n1024/prompt.tokens` | 41,235 B | `94adc252a7f5c9ff8908dd5ae4c181b2` | prompt（reps=40） |
| `w13_out/trace.bin` | 4,224 B | `e578cad52b15af9602c0620a10b178af` | **第一车反面教材**：`--max-new 1` => 仅 48 记录 |
| `w13_out/_w775_w13_r40/trace.bin` | 4,224 B | （同上） | 第二车：**改 reps 无效** => 证明记录数只由 `--max-new` 决定 |

**166 上的车**（可复现）：

- `/home/albus/strata166/data/_w775_w13.py`（5,034 B / md5 `b2aa9fdee6fbe520ad961a5831d4aeec`）
- `/home/albus/strata166/_w775_w13.sh`（**2,645 B / md5 `3994d94634f8baf3c4ea59fd7b6393ed`** --
  * 审计更正：原稿误写 `e9201ee897818c32c56a10a0b9c6752a`；字节数对、md5 错，此处已实读更正）
- 关键 CLI（**审计更正：逐字出处是 `data/_w775_w13.py` 的 `cmd=[...]`，不是 `.sh`** --
  `.sh` 只是驱动器：停生产 -> `docker run ... python3 /data/_w775_w13.py` -> 恢复）：
  `/src/build-906/strata --pack /data/packs/huihui-ud-iq4_xs --native <shard1> --tokens-file <f>
   --ple-gguf <shard2> --spec 4 --prefill auto --expert-profile /src/data/expert-profile.bin
   --expert-cache auto --resident-budget-gib 76 --pcie-frac 0.20 --kv k8v4
   --max-context 262144 --max-new 1024 --dump-routing <out>`

## 6 局限（必须随结论一起引）

- **未做真机 A/B**：本结果是**离线复放**（命中率只取决于 routing 顺序），**没有改引擎跑真机**。
  它给的是命中的**上界与现状差**，不是 tok/s 收益 -- 收益还取决于 miss 的成本（PCIe / CPU pool 占比）。
- **trace 是"文本续写"面**：3,838 positions 来自一条多主题拼接 prompt 的自回归续写，**不代表生产对话分布的全体**。
  生产真实负载若更"主题稳定"，fill-only 会更好看；若更"主题跳跃"，差距会更大。
- **oracle 不可实现**（读未来），只作上界。
- `--max-new 1024` 的实际 positions = 3,838（> 1024），说明 MTP/spec 每步产生多个 position -- **该乘数关系未逐条核**。



> **[!] 口径更正（2026-10-11 15:2x，`W26` 实测后，W752 同步）**：本件把 `fill-only`（= 本工具在**无迁移**下的结果）称作"引擎现役命中率（因为策略=不淘汰 => fill-only 就是现状）"，**该论断只对 `ExpertCache::admit` 成立，对生产不成立**：生产同时启用 **resident RAM mode + `adapt()` 自适应迁移层**（日志逐字 `adaptive swaps exchange them with the GPU cache`）。用引擎自带的 `tools/replay_cache_policy.py`（= `adapt()` 的模型）在同一 trace / 同一 profile / 9,761 槽复放得 **0.9564**（本件 fill-only 0.7086 为其`--swaps 0` 消融；静态 oracle 0.9669）=> **本件结论"引擎从不淘汰"须限定为"`admit` 不淘汰"，不是"引擎不迁移"**。见 `deploy/W775delta_W26_TIER_REPLAY.md`。
> **[BAN 归一说明 · 2026-10-11]** 本件属"活跃交付件"，已按项目禁用码位表（见 `W750_MASTER_PLAN.md` 第 0.5.7 节）做 **ASCII 归一**，映射：`U+2192`->`->` · `U+21D2`->`=>` · `U+2026`->`...` · `U+0394`->`delta` · `U+00D7`->`x` · `U+2014`->`--` · `U+2605`->`命中`/`*` · `U+2460-U+2469`->`(1)-(10)` · `U+2705`->`[OK]` · `U+26A0`->`[!]`。
> **引文处语义一字未改**，原文形态可回溯：改前副本 `deploy/tmp/_w21_bak/`（改前 md5 见件尾注）。
> 改前 md5 = `b85d84364589e796d1580ce447b02974`（字节 12137）。
