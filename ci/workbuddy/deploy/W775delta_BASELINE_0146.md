# 0.1.46.2 基线实测（三臂）+ 上游建议融合评估（2026-10-21）

> **触发**：机主令「生产 config 是否可以跟上游建议做一下融合。然后跑新基线」。
> **形状**：一次停机窗口（22:44 至 22:58，约 14 min），三臂顺序跑，每臂独立容器、独立日志、`trap` 兜底恢复生产。
> **口径**：**实测**（引擎自己的 per-request 行）· **源码**（`src_latest` = 0.1.46.2）· **上游逐字**（release note）。decode 仅 2 runs，**按我们自己的纪律（decode 需 5+ runs，spread 14-40%）不作结论**。

---

## 一、三臂定义

| 臂 | 引擎 | config | 关键差异 |
|---|---|---|---|
| **R**（参照） | **0.1.42**（镜像内 `/src/build-906/strata`） | `_bR.json` | 生产 config 原样（只改 `log`/`port`） |
| **N**（新版基线） | **0.1.46.2**（`/src/build-906-doc/strata`，官方配方） | `_bN.json` | 同上 + `exe` 指向新二进制 |
| **F**（融合） | **0.1.46.2** 同上 | `_bF.json` | 同上 + `STRATA_ROUTE_TAIL_SKIP=0` + `--ple-io direct`（显式） |

三者除上述外**逐字节相同**：同一 pack、同一 `--kv k8v4`、同一 `--resident-experts`、同一 `--max-context 262144`、同一 `--spec 4`（实跑 spec=6）。

---

## 二、原始读数（2 档 x 2 runs，`reused=0`、`cached=0`）

### 3K 档（实际 ptok = 2,401）

| 臂 | read_ms | prompt tok/s | gen tokens | decode tok/s | wall |
|---|---|---|---|---|---|
| R (0.1.42) | 6,518 / 6,260 | **368.4 / 383.5** | 47 / 47 | 41.7 / 46.7 | 7.7 / 7.3 s |
| N (0.1.46.2) | 6,623 / 6,195 | **362.5 / 387.5** | 47 / 47 | 37.9 / 50.0 | 7.9 / 7.2 s |
| F (0.1.46.2+融合) | 6,604 / 6,269 | **363.6 / 383.0** | 47 / 47 | 34.7 / 42.3 | 8.0 / 7.4 s |

### 26K 档（实际 ptok = 20,238）

| 臂 | read_ms | prompt tok/s | gen tokens | decode tok/s | wall |
|---|---|---|---|---|---|
| R (0.1.42) | 42,148 / 42,360 | **480.2 / 477.8** | 49 / 49 | 46.8 / 55.4 | 43.2 / 43.3 s |
| N (0.1.46.2) | 42,029 / 42,276 | **481.5 / 478.7** | 49 / 53 | 46.7 / 50.8 | 43.1 / 43.4 s |
| F (0.1.46.2+融合) | 41,925 / 42,269 | **482.7 / 478.8** | **66 / 29** | 38.3 / 54.2 | 43.7 / 42.8 s |

---

## 三、结论（三条，全部有原始读数支撑）

### 1. **版本间没有可测差异**（这是本次最重要的结论）

- prompt 读：3K 档三臂 **362.5 - 387.5 tok/s**、26K 档 **477.8 - 482.7 tok/s** —— **全部落在同一噪声带**。
- 这与上游自己的说法一致：0.1.43 的 AMD 提速**逐字限定 RDNA4**，`RDNA3 (gfx11) and older keep their 0.1.42 behaviour`。**gfx906 不在任何一次提速的覆盖里**。
- ->  **"升级能变快"这个假设被实测否掉**。升级的价值只能在**修复/稳定性**，不在速度。

### 2. **融合（`ROUTE_TAIL_SKIP=0` + 显式 `--ple-io direct`）对 prompt 没有收益**

- 3K：N 中位 6,409 ms vs F 6,437 ms（**+0.4%**）；26K：N 42,153 vs F 42,097（**-0.1%**）。
- 都在噪声内。->  融合**不提升吞吐**。

### 3. **融合确实改答案**（这一点必须单独说）

- 26K 档输出 token 数：R/N = 49/49、49/53，**F = 66/29** —— 同一 prompt、同一 greedy，输出长度明显不同。
- 这正是 `STRATA_ROUTE_TAIL_SKIP` 的已知性质（上游逐字：skip 会让答案"differ slightly"，KL 0.003-0.006）。**关掉它 = 回到更保守的路由**，代价是丢掉 +10~20% 的 decode 上限（在会 miss 的卡上；我们 miss 很少）。
- ->  **这是一次"质量 vs 速度"的取舍，不是免费优化**，且需要 5+ runs 才能判 decode 侧代价。

---

## 四、本波顺带纠正/发现的三件事

| # | 事项 | 证据 |
|---|---|---|
| **1** | **我此前推断"0.1.46.2 会自动关掉 ROUTE_TAIL_SKIP"——错的** | 实测：0.1.42 与 0.1.46.2 **都打印** `STRATA_ROUTE_TAIL_SKIP=7 is ON (default)`（`all_experts_resident` 在我们配置下为 false）。**推断被实测推翻。** |
| **2** | **新版多了一个我们从未见过的开关：`STRATA_ADAPT_OVERLAP_RESIDENT=1`** | 0.1.46.2 启动行逐字：`adaptive overlap: off: not in the resident RAM mode unless STRATA_ADAPT_OVERLAP_RESIDENT=1`。0.1.42 没有这行。**这正是针对 `--resident-experts` 模式的自适应 copy 重叠**，是唯一有速度潜力的新项。 |
| **3** | **GPU 读图器抢 1.47 GB 的风险在我们这里不成立** | 两臂启动段都打印 `strata-vision: on the CPU, 22 threads`；我们自建镜像只编 `strata`，**没有 `strata-vision-hip`**，故 CPU 读图器固定。 |

**另**：PLE 两臂都是 `PLE direct read probe: 34866 / 34323 rows/s (fine)` ->  **direct 臂**（与 10-18 的 34,235 一致），生产 config 里**不传 `--ple-io` 也是 direct**。显式写的唯一价值是"不依赖探针状态"，属纪律项，不是性能项。

---

## 五、"生产 config 能不能跟上游建议融合"——结论

**能融，但只有 2 条，且都不是性能项；另有 1 条新候选值得单独测。**

| 项 | 上游建议（逐字要点） | 我们现状（实测） | 判定 |
|---|---|---|---|
| `STRATA_ROUTE_TAIL_SKIP=0` | 0.1.44 为 Unsloth 文件写入：*where every expert is in RAM，skip 在那里让 KL 0.056 -> 0.086 换 +4-10% 速度* | **ON(default)**，实测改答案 | **本车已测：prompt 无收益，答案改变**。->  若要质量优先可采纳；要速度优先则不采纳。**建议保持现状（ON），除非你更看重答案保真** |
| `--ple-io direct` 显式 | 0.1.45 起不再自动切 mmap | 不传，实测 direct | **建议显式写入**（0 成本、去掉对探针的隐式依赖） |
| **`STRATA_ADAPT_OVERLAP_RESIDENT=1`** | 本波新发现（0.1.46.2 启动行） | 未测 | **建议列为下一个单变量候选**（唯一有速度潜力） |
| `STRATA_PIN_BY_NEED=1` | Windows/WDDM 特性 | Linux + 已 page-locked 补集 | **不采纳** |
| `--parallel N` | 单用户 -4~-11%，N 并发 1.0-1.15x | 单流 | **不采纳**（W9 已判） |
| `--prefill-head-alias` | 8 GB 卡省显存 | 32 GB，`574 MiB` 空闲 | **不适用** |
| `--prompt-cache-spread` / `--conversation-cache-park-gain` | 新 opt-in，多轮/重写历史 | 多轮（open-webui） | **候选，需单独测**，本车未带（避免多变量） |

**一句话**：**上游建议里没有一条能在我们这套 gfx906 配置上直接变现为吞吐**；能动的只有"答案保真"和"纪律"两类。真正值得再花一个窗口的，是本波新发现的 `STRATA_ADAPT_OVERLAP_RESIDENT`。

---

## 六、部署终态

- 生产已恢复：`/health` `"loaded": true`，启动耗时 **45 s**；`strata166-407 | Up`。
- 生产 config **md5 `ff8cb97379f0bdbe76ee555da6d8729c` 未变**（全程只用副本）。
- 三份副本与日志保留：`/home/albus/strata166/data/_b{R,N,F}.json` / `_b{R,N,F}.log` / `_bench_{R,N,F}.csv`。
- 脚本：`/home/albus/strata166/_b023_run3.sh`、`_bench.py`。

**未改任何生产参数值；未动生产 config；未发任何上游内容。**
