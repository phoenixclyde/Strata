# W781 遗留项四项的「可移植性」深度判定

> 2026-10-25 01:5x-02:4x · 机主令：「这里面有没有可以移植过来的，深度分析，必要时上网查。其他你继续。」
> 对象 = `W780` §5 的 4 项遗留（calibrate / kv-grow / 8K 复用 / 合规基线）
> 结论先行：**四项里没有一项需要"移植代码"——三项的工具和源码本来就在我们的树里；剩下那项（8K 复用）上游根本没修，没有东西可移。**

---

## 0 一句话结论

| 遗留项 | 原先的判断 | 实际判定 | 依据 |
|---|---|---|---|
| `--spec-min-p --calibrate` | "要移植上游校准工具" | **不需要移植。`tools/calibrate.py` 一直在源码树里，纯标准库、原生支持 HIP** | §1 |
| `--kv-grow` | "要移植 kv-grow 实现" | **不需要。`kvg_start/kvg_ensure` 在 0.1.49.2 的 `generate.cpp` 里就有；卡的是 `--resident-experts` 这个互斥门** | §2 |
| 8K 以下复用 | "属上游机制问题，只能上报" | **确认无现成方案可移**（vLLM / llama.cpp 的缓存机制结构不同）；根因锁到两行源码；**上游已有两个相关 issue 在跟** | §3 |
| 合规基线 | "官方 runner 用不了" | **不准确。`bench/prompts/standard-v1` 与 `strata_control` CLI 都在树里，只是我们只编了引擎** | §4 |

**"其他你继续"已经执行：`tools/calibrate.py` 已在 166 上开跑**（§5）。

---

## 1 calibrate：工具一直都在，我们漏了一年

### 1.1 它是什么

`tools/calibrate.py`（源码树根下），文件头原文：

> `"""Tune the engine's hardware-dependent settings on this PC (setup's --calibrate).`
> `Three settings depend on the machine more than on the model …`

它一次校 **5 组参数**，不是只有 `--spec-min-p`：

| 参数 | 候选 | 我们的现值 | 备注 |
|---|---|---|---|
| `--pcie-frac` | `0.0, 0.2, 0.35, 0.55, 0.75, 0.9, 1.0` | **0.20** | **从 W712 时代沿用至今，从未在本机校过** |
| `--spec-min-p` | `0.3, 0.5, 0.7` | **0.70** | 上游 setup 默认 0.5，我们是历史值 |
| `--pool-workers` | 默认 + `P-cores-1` + `socket_cores-1` | 默认 20 | 需重启 |
| `--adapt-every/swaps/decay` | `None / (1,80,0.97) / (1,160,0.97)` | 未设 | 需重启；P27 当年判 REJECTED |
| `STRATA_SH_STREAM` | 0 / 1 | 未设 | HIP 专属，需重启；P40 当年判 REJECTED |

判定规则（源码常量）：`MIN_GAIN = 0.03`（3%）、`SWEEP_ROUNDS = 3`（三轮交错），**只有"每轮都更快且中位数超 3%"才保留** —— 这比我们手工单变量扫描的纪律更严。

### 1.2 为什么能在 gfx906 上跑（依赖链逐项核过）

| 依赖 | 状态 | 证据 |
|---|---|---|
| Python 第三方库 | **零** | import 只有 `json / statistics / sys / threading / time / pathlib` |
| `import setup` | **可选**（包在 `try/except` 里，失败返回 `[]`） | `calibrate.py` 的 `host_worker_extras()` |
| `StrataEngine` | 在 `serve/server.py:952`，**我们镜像里就有** | `grep -rn 'class StrataEngine'` |
| tokenizer 三件套 | **齐全**（容器内实测） | `vocab.json` 5,737,005 B / `merges.txt` 3,353,258 B / `token_type.json` 744,960 B |
| `strata_tokenizer` 模块 | 容器内 `import strata_tokenizer` **通过** | 实测输出 `tokenizer module ok` |
| HIP 支持 | **原生** | `hip=cfg.get("backend") == "hip"`，第 245/247 行 |

**所以"移植"这个动作根本不需要发生。** 我们之前说"官方 runner 用不了"，是因为只编了引擎、没意识到 CLI 层是纯 Python 且随源码一起发。

### 1.3 唯一真正的坑：stdout 缓冲

`python3 tools/calibrate.py cfg.json > out 2>&1` 时 Python 用 4 KB 块缓冲，**进度行攒不满 4 KB 就一个字都不写**。实测跑了 6 分钟 `calib.out` 仍然是启动那 8 行、而 GPU 占用 99%——它在干活，只是不吭声。

**下次必须加 `-u`**（`python3 -u tools/calibrate.py`）。这次已开跑的不动它（重启会丢掉已测的值）。

---

## 2 kv-grow：不是移植，是拆一个互斥门

源码在（`generate.cpp` 的 `KvGrow` 结构 + `kvg_start` / `kvg_ensure`），门槛逐字：

```cpp
const bool on = asked && !multi_gpu && o.kv_resident <= 0 &&
                !o.expert_profile.empty() && !o.resident_cpu_experts && ...
```

而 `--resident-experts` = `--mmap-experts --resident-cpu-experts`（help 原文），所以我们**一直开着 `resident_cpu_experts` => kv-grow 从来没生效过**。

**要做的不是移植，是换一组参数**：
- 去掉 `--resident-experts`
- 保留 `--expert-profile /src/data/expert-profile.bin`
- 打开 `--kv-grow`

代价与收益（W776 已算）：+1487 槽（+15.2%），省下 36.93 GiB pinned 副本；风险是专家改依赖 page cache（现在 63 GB 已缓存，但可被回收）。

**这一步需要单开窗口 + 明确的回滚判据**，不属"移植"范畴。

---

## 3 8K 以下复用：没有东西可移，但根因已锁到两行

### 3.1 根因（0.1.49.2 源码，行号可核）

`src/program/generate.cpp` 的 chunk 完成回调：

```cpp
const int64_t done = p0 + T;                                    // 9903: 一个 chunk 读完才更新
const bool periodic_checkpoint = o.prompt_cache_every > 0 && done >= pp_next_check;   // 9907
...
if (periodic_checkpoint) pp_next_check = done + o.prompt_cache_every;                 // 9930
```

- 回调**只在 chunk 边界触发一次**；
- 7,342 token 的对话，`done = 7342`，而 `pp_next_check` 初值是 `prompt_cache_every = 8192`；
- `7342 < 8192` => **永不 checkpoint** => 第二轮 `reused = 0` => 从头再读 15 秒。

`--prompt-cache-tail` 也救不了：它的条件是 `pp_total - done > max(1, short_read)`，而我们 `pp_total == done`（整段就是一个未满 chunk），差值 0，不触发。**这与 P21 当年的实测结论一致，但这次给出了根因。**

### 3.2 上网查的结果：上游有两个直接相关的 open issue

| issue | 日期 | 内容 | 对我们的意义 |
|---|---|---|---|
| **#3950** | **2026-10-24** | 「0.1.48 engine: random **10-80 s TTFT spikes on short chat requests** (not in 0.1.44.1)」—— 同一台 RTX 3090、**同样是 Qwen3.8-Flash-Next**、参数几乎一致（`--kv int8 --spec 4 --spec-min-p 0.70 --expert-cache auto`），升到 0.1.48 出现短请求尾延迟尖峰 | **我们正在跑 0.1.48.1/0.1.49.2，且短对话本来就慢**。这条说明"短请求慢"不全是我们的复用问题，可能还叠加了 0.1.48 引入的尖峰 |
| **#3667** | 2026-10-22 | 「0.2.2 short replies lose **15-30% in `serve/server.py`, not in the engine**」—— 交叉 2×2 证明同一个引擎二进制在 0.1.44.1 的 server 下快、在 0.2.2 的 server 下慢 | **我们生产正是 `python3 serve/server.py`**。如果这条成立，我们一直背着 server 层的 15-30% 短回复损失 |

两条都还 **open 且只挂着机器人提醒**，没有维护者结论。=> **没有可移植的修复。**

### 3.3 能不能从别处搬？（查过了，不能）

| 来源 | 机制 | 为什么不可移 |
|---|---|---|
| vLLM prefix caching | 按 KV block 的 hash 命中，块级复用 | 它有自己的 paged KV + block manager；Strata 是自有 QSA layout + 会话 checkpoint，**没有 block 表可对齐** |
| llama.cpp `--prompt-cache` / slot | 冷启时按 token 前缀序列化到磁盘 | 它是**请求级**的文件快照，不是 serve 内的增量 checkpoint；语义不同 |
| routeK（KIntegrated） | vLLM 同上 | W779 已判：布局不通 |

### 3.4 唯一可行的本机改法（建议先报上游，再决定要不要打）

改动极小：让"整段不足一个 chunk"的请求在结束时补一个 checkpoint。

```cpp
// 概念补丁：periodic_checkpoint 之外，补一个"整段就是一个未满 chunk"的终点 checkpoint
const bool short_whole = o.prompt_cache_every > 0 && pp_total > 0 && pp_total < o.prompt_cache_every &&
                         done >= pp_total && !pp_short_saved;
if (periodic_checkpoint || tail_checkpoint || short_whole) { ... if (short_whole) pp_short_saved = true; }
```

- **收益**：8K 以下对话第二轮 `reused = 7342`，首字从 15 s 降到 2 s 量级（按 19.5K 那档 40.4->8.1 s 的同比推算）。
- **代价**：每个请求多存一个 checkpoint（约 118 MB/个，`--prompt-cache 6` 上限不变）。
- **风险**：**偏离 upstream**，每次升版重打；且改动落在 serve 的热路径。
- **建议顺序**：先把 §3.1 的证据发到 #3950 / 新开一个 issue（附 7,342 与 19,467 的对照）-> 等维护者说法 -> 再决定自打补丁。

---

## 4 合规基线：工具比我们以为的多

| 资产 | 位置 | 状态 |
|---|---|---|
| 冻结 fixture | `bench/prompts/standard-v1/`（含 `MANIFEST.sha256`） | **在镜像里** |
| 对照脚本 | `bench/bench_vs_llama.py` | 在 |
| AB 工具 | `tools/ab_engine.py`、`tools/strata_bench.py`（#3667 用的就是它） | 在 |
| 官方 runner `strata bench run` | `strata_control/` + `bin/strata` | **在**（0.2.4 树里有完整 CLI，只是没装依赖；`bin/strata` 是 5756 B 的 sh 启动器） |

结论：合规基线**不需要移植**，是把 `strata_control` 跑起来（纯标准库？待确认）或直接照 fixture 手工发请求。

---

## 5 已执行：calibrate 正在 166 上跑

| 项 | 值 |
|---|---|
| 启动 | 2026-10-25 01:54:30 |
| 方式 | 停生产 -> `docker run --rm --name strata-calib`（同 GPU 权限/binds）-> `python3 tools/calibrate.py /data/strata-huihui-ud-iq4_xs.json` |
| 守护 | 外层 shell 脚本 `calib_run.sh`，**跑完自动 `docker start strata166-407`**（即使 calibrate 崩溃也会恢复） |
| 输出 | `/home/albus/strata166/data/calib.out`（被块缓冲，跑完才有完整内容） |
| 现状 | 引擎加载正常（`filling the GPU's expert cache (9901 experts, 22.31 GiB)`），GPU 占用 99%，无报错 |
| 预计 | 30-90 分钟（`SWEEP_ROUNDS=3` × 多组候选 × 128/512 token 输出 + 每值重启式测量） |

**注意**：校准期间生产不可用（生产容器已停）。跑完自动恢复。

---

## 6 下一步（按顺序）

1. **等 calibrate 出结果** -> 若 `--pcie-frac` 的 0.20 不是最优（很可能，因为从没在本机校过），这是本轮最大的单项收益
2. **把 §3.1 的证据整理成 issue** 发到上游（附 7,342 / 19,467 两档对照 + 两行源码）——这是唯一能让 8K 问题根治的路
3. `--kv-grow` 单开窗口（拆 `--resident-experts`）
4. 合规基线（fixture 已在镜像里）

---

## 7 一句话

**问"能不能移植"的答案：三项是"工具和源码本来就属于我们，只是没启用"，一项是"上游自己也还没修、而且没有别家的机制能套过来"——所以真正该做的不是移植，是把 `calibrate.py` 跑起来、把 8K 的根因发给上游。**
