# W774 上游 v0.1.42 升级 + 对外件回音审计

**时间**：2026-10-11 00:0x ~ 00:5x CST（读）+ 00:52 发车（测）
**轴**：上游 `Niko1221/Strata`；我们对外的 PR / issue / 评论**逐件现查**
**Z0 声明**：本节所有 GitHub 读数均为**匿名 API 现查**（`api.github.com`），非记忆、非推测
**通道声明**：**读通道可用**（匿名 API）；**写通道当前不可用**（GCM 无 GitHub 凭据，见 §5）

---

## 1 v0.1.42 现状

- 上游 main 自 10-08 前进到 **v0.1.42**（发布 **2026-10-11 00:10 CST**）。
- release notes 全文 **23,126 字符**（已读全）。
- 我们据此登记 **P55-P60**（见 §4 与 `PARAM_REGISTER.tsv`）。
- 构建镜像 **`strata-gfx906:0.1.42`（6.59 GB）**，`PATCH_SURFACE_ZERO`（patched=0 / verified=6 / failed=0）。
  引擎指纹（md5）：0.1.41 = `160611838796d4b172ec3a642ccd988d`；0.1.42 = `5efa1d45c2e8c6f14b62a96b32d03155`。

---

## 2 对外件逐件现查（2026-10-11 00:4x，匿名 API）

| 件 | 类型 | 状态 | 维护者回音 | 判定 |
|---|---|---|---|---|
| **#1731** | PR | `closed`, `merged=False`, comments=1 | Niko1221 2026-10-10 16:32:50Z：*"Thank you, in v0.1.42 with your authorship. The floor of 1 only lowers the axis, so a real burst keeps its scale and the cards that pass a maximum are untouched."* | **已采纳（ported）**，署名保留 |
| **#1732** | PR | `closed`, `merged=False`, comments=1 | 16:32:56Z：*"...in v0.1.42 with your authorship (the MI50 measurement is what made the mechanism clear). The gfx906 build no longer takes the CUDA branch of arm_cpu_share, so the CPU share is not armed by default there..."* | **已采纳（ported）**，**且明说我们的 MI50 测量是澄清机制的关键** |
| **#1733** | PR | `closed`, `merged=False`, comments=1 | 16:33:02Z：*"...The AMD reader now reports the narrowest and slowest PCIe hop (only when every hop could be read), the card's own hop, and how many hops were read. The throughput counters are left out for the reason you gave..."* | **已采纳（ported）**，且**"吞吐计数按我们给的理由舍弃"** |
| **#1855** | PR | `open`, comments=0 | 无 | 社区 bench 报告，**仍开放待并入** |
| **#1734** | issue | `open`, comments=0, updated 10-09 | **无** | **待跟进**（见 §3） |
| **#1735** | issue | `open`, comments=0, updated 10-09 | **无** | **待跟进**（见 §3） |
| **#1595** | 评论所在 issue | `open`, comments=2 | 16:20:51Z：*"Thank you for the clean interleaved table. You were right: the 0.1.41 CPU prefill share default has nothing to take when every expert is already in the GPU cache... **In v0.1.42 the default share is not armed when the expert cache holds every expert**..."* | **正确性被确认**，机制已按我们的分析修正 |
| **#1729** | 评论所在 issue | `open`, comments=2 | 16:34:27Z：*"Thank you for the detailed log analysis, the GPU power and the split by session were exactly what we needed to look at. We tried to reproduce the decode loss on two CPUs without AVX-512..."* | **被采纳为调查起点** |
| **#1479** | 评论所在 issue | `open`, comments=2 | 16:18:05Z：*"**Added as HIP opt-ins (your patch, you are credited as co-author)**: STRATA_HEAD_MIX_MULTI=1 and STRATA_ONE_TOKEN_COMMIT=1, default off. Tested on 2x R9700, IQ3_S... answers identical in all runs; decode speed was not distinguishable..."* | **我们的发现被直接采纳为代码**（新增 P59/P60） |
| **#1670** | 评论所在 issue | `open`, comments=3 | vizdatom 提供 `perf-ryzen` 分支；我们已留言愿跑 | **我们主动提议但未兑现**（见 §3） |

**汇总结论**：**我们对上游的每一条主动贡献都得到了正向回应**（3 PR 全合入 + 1 采纳为代码 + 2 确认为正确 + 1 采纳为调查起点）。
唯一的两个"零回音"是我们自己开的 **#1734/#1735**（Monitor 两个观察），提交仅 2 天。

---

## 3 需要动作的三条

1. **#1734 / #1735**（我们开的，0 回复）：两条都写成"提方案问维护者选哪个"。
   - #1734（PCIe tile 的 `pcie_rx_mb` 方向性）：我们**已有可用的 link 半 patch** = `phoenixclyde/Strata@5241c728`（分支 `amd-monitor-pcie-link`）。
   - **动作**：在 #1734 贴出该分支链接，让维护者可直接取用。**需写通道**。
   - **暂不催**（2 天，且维护者刚在批量回复）。
2. **#1670（vizdatom layer-major prefill）**：我们已留言"可以跑你的分支"，但**未兑现**。
   - 机制 = 对未驻留专家做 layer-major 预取以减 S/512 重读；与我们 **P33 / P46** 族相关。
   - **前置**：`STRATA_PREFILL_LAYER_MAJOR` 需先在本机 HIP/gfx906 编译通过（其 base = 0.1.39 + 10 commits）。
3. **#1855（我们的 bench PR）**：仍 open 待并，**无需动作**，观察即可。

---

## 4 登记（P55-P60）

| ID | 项 | 状态 | 出处 |
|---|---|---|---|
| P55 | `STRATA_GFX906_ATTN_QUERY_SWIZZLE` | CANDIDATE | PR #1661（0FL01），已进 0.1.42，上游无 MI50 验证 |
| P56 | `STRATA_GFX906_ATTN_REDUCE12` | CANDIDATE（依赖 P55） | PR #1718（0FL01） |
| P57 | v0.1.42 非 gfx906 开关族 | REJECTED（封口） | release notes 逐条 |
| P58 | v0.1.42 通用新项 | REFERENCE | release notes；两条列待办 |
| P59 | `STRATA_HEAD_MIX_MULTI` | CANDIDATE | **#1479 维护者采纳**（署名我们） |
| P60 | `STRATA_ONE_TOKEN_COMMIT` | CANDIDATE（与 P59 同 patch） | **同上** |

register => **75 行数据**（ADOPTED 26 / REJECTED 32 / CANDIDATE 11 / REFERENCE 6）。

---

## 5 通道状态（现查现证）

- **读**：`api.github.com` 匿名 GET -- **可用**（本文档所有状态均由此读得）。
- **写**（发评论 / 开 PR）：**当前不可用**。
  - 证据：`git credential fill`（GCM 配方，`GIT_CONFIG_COUNT=2` 先空后钉 `git-credential-manager.exe`）取回的是 **prompt 文本**（89 B，以 `Passwo` 开头、以 `m': ` 结尾），而非 token；
  - `git-credential-manager.exe github list` 输出**为空** => GCM 凭据存储当前**无 GitHub 凭据 / 未解锁**。
  - 对比：W736/W771 时同一配方可成（那时 GCM 刚登录、token 在半会话缓存里）。
  - **解法**：**机主在任意 git 操作或 GCM 弹窗里登录一次 `phoenixclyde`** 即可恢复；之后 #2/#3 的写动作可自动完成。
  - 纪律：凭据**只在内存里用，不打印、不落盘**（W736 §8.1）。

---

## 6 W774 发车（00:52 重发，5 臂）

| 臂 | 镜像 | env 增量 | 回答 |
|---|---|---|---|
| `p41` | 0.1.41 | （无） | 基线 |
| `p42` | 0.1.42 | （无） | **升级无回归？**（p42 vs p41） |
| `sw1` | 0.1.42 | `+STRATA_GFX906_ATTN_QUERY_SWIZZLE` | **P55**（sw1 vs p42） |
| `sw2` | 0.1.42 | `+QUERY_SWIZZLE +ATTN_REDUCE12` | **P56**（sw2 vs sw1） |
| `hm1` | 0.1.42 | `+HEAD_MIX_MULTI +ONE_TOKEN_COMMIT` | **P59+P60**（hm1 vs p42） |

- 负载：`_w773_speed.py`，32768 / 128000 各 2 runs，max_tokens 256，每 run 新 nonce（`reused` 全 0）。
- **主口径 `ms/step`**；`tok/s` 受净出污染（W773 实测臂内 spread 达 27%）=> 仅作参考。
- **首发两处血证（已修）**：
  1. arm 循环用 `:` 作分隔符，与镜像名自带的 `:` 冲突 => docker run 收到 `0.1.41:latest` 失败。**已改 `|`**。
  2. **同一脚本被 `ssh nohup &` 与 `setsid &` 各启一份**，抢同一容器名 / 端口，且 `trap restore EXIT` 在对方被 kill 时重启生产、删对方容器 => **数据污染**。**已加 `flock` 单实例锁 + `RESTORED` 幂等 guard**，清场后重发（唯一实例，锁获取已证）。

### 6.1 实测进度（00:52 ~ ）

- **p41 臂**（0.1.41 基线）00:52:26 起，`ready after ~105s`；32768 档两 run 已出：
  - run0：prompt 26036 tok = **0 reused + 26036 read** in 57735 ms（**451.0 tok/s**），gen 256 in 7241 ms
  - run1：prompt 26037 tok = 0 reused + 26037 read in 56504 ms（**460.8 tok/s**），gen 256 in 5982 ms（**42.8 tok/s**）
- 运行期取证（p41）：`引擎 --kv: k8v4` 在位；`expert cache 9761 experts, 21.99 GiB`；decode 命中 92.6%。
- 每臂约 5-6 分钟负载 + ~105s 加载 => 5 臂预计 **~40 分钟**（约 01:30 收车）。

## 7 结论（2026-10-11 01:43 收车，`ARMS_FAIL=0`）

### 7.1 收车事实

```
ARM_p41=DONE 01:03:25 / ARM_p42=DONE 01:13:17 / ARM_sw1=DONE 01:23:12
ARM_sw2=DONE 01:33:09 / ARM_hm1=DONE 01:43:02
ARMS_FAIL=0 / W774_ALL_ARMS_DONE 01:43:16
[restore] prod ready -> HTTP=200 01:43:56（生产 strata166-407 恢复）
verify_config.py: PASS=26 FAIL=0
```

5 个 speed JSON 齐备（各 4 records，共 20 条），全部 `reused=0`（nonce 生效，每 run 都是新工作）。

### 7.2 一个必须先声明的口径缺陷（**新发现，影响 p41 的可比性**）

负载脚本 `_w773_speed.py` 的 `filler()` 从 **`/src` 下的仓库源文件**（`docs/*.md` + `src/*.cpp` + `include/*.hpp`）拼 prompt。而 `/src` 是**每个镜像自带的树**：

| 臂 | 镜像 | prompt 实测 tok（小档 / 大档） |
|---|---|---|
| p41 | 0.1.41 | 26036 / 93338 |
| p42/sw1/sw2/hm1 | 0.1.42 | 23781 / 93999 |

=> **小档跨版本不可直接比**（26036 vs 23781 = **+9.5% 内容量**，p41 天然更重）；大档差 0.7%（可忽略）。`tok/s` 因是引擎自算的 tokens/ms 比值，**各臂自洽可比**；`prompt_tokens` 与 `wall_s` 跨臂不可比。

### 7.3 主口径判读：prompt 侧（干净可判）

`prompt ms/step = read_ms / read_tok`，两 run 均值：

| 组 | 对照 | 小档 32768 | 大档 128000 |
|---|---|---|---|
| 0.1.42 升级 | p41->p42 | 2.1938 -> 2.1201（**-3.36%**，受 7.2 污染） | 2.2054 -> 2.1903（**-0.69%**） |
| P55 QUERY_SWIZZLE | p42->sw1 | 2.1201 -> 2.1200（**-0.00%**） | 2.1903 -> 2.1888（**-0.07%**） |
| P56 REDUCE12 | sw1->sw2 | 2.1200 -> 2.1210（**+0.05%**） | 2.1888 -> 2.1889（**+0.00%**） |
| P59/P60 HEAD_MIX+ONE_TOKEN | p42->hm1 | 2.1201 -> 2.1211（**+0.05%**） | 2.1903 -> 2.1986（**+0.38%**） |

**=> 判定：`P55` / `P56` / `P59` / `P60` 对 prefill 全部中性**（|delta| ≤ 0.4%，远小于测量分辨率）。`0.1.42` 升级本身在 prefill 上**无回归**（大档 -0.69%，在噪声内；小档的 -3.36% 由 7.2 的口径缺陷解释，不作为回归证据）。

### 7.4 decode 侧（`decode ms/step = gen_ms / gen_tok`）：**弃权**

| 臂 | 小档 spread | 大档 spread |
|---|---|---|
| p41 | **21.0%** | **16.2%** |
| p42 | 3.1% | 3.9% |
| sw1 | 0.2% | 9.2% |
| sw2 | 5.0% | 1.0% |
| hm1 | 1.9% | 6.3% |

组间差（`p42->hm1` 小档 +4.53% / 大档 -2.97%；`p41->p42` 大档 +17.86%）**全部落在臂内 spread 之内或量级相当**。按 W773 立下的纪律（"臂内 spread 才是真判据"），**decode 组间差不可判，结论弃权**，需 5+ runs 才能收敛。

补充的**计数型**指标（不受 wall-clock 抖动影响）同样不可判：

| 组 | 对照 | 小档 接受率 | 大档 接受率 |
|---|---|---|---|
| 0.1.42 升级 | p41->p42 | +15.61%（**p42 小档仅 36 个 draft 的 run0 把均值拉高，样本不足**） | **-11.01%** |
| P55 | p42->sw1 | -6.88% | +1.14% |
| P56 | sw1->sw2 | -4.97% | +2.19% |
| P59/P60 | p42->hm1 | -8.61% | +3.26% |

符号在小/大档**互相反转** => 无一致信号。唯一值得记的是 **0.1.42 大档接受率 -11.0%**（p41 79.8% -> p42 71.1%），但 p41 大档只有 2 runs 且自身 spread 16%，**不足以定罪**，列为待复核。

### 7.5 连带裁决（本次一并完成）

| 项 | 结论 | 依据 |
|---|---|---|
| **§6.4 #5 `STRATA_PLE_PROBE` 升级副作用** | **[更正 2026-10-14] 原判「对生产不适用（不可达）」作废，实为「可达且已在动作」** | 生产日志（serve 启动行 L2714 之后）实读：`PLE on, table 320001536 rows` **38 次**、`--ple-io direct measures slow here (14560 / 13268 rows/s): using --ple-io mmap instead` **2 次**，即 PLE 表**已加载**、探针**已执行**、生产 `--ple-io` **已被自动切成 `mmap`**。原论据「无任何 `PLE ... rows/s` 行」是过窄 grep（实际行首为 `--ple-io`）。见 `W775delta_UPSTREAM_MAILCHECK_20261014.md` §E。 |
| 机制修正 A | `STRATA_PLE_PROBE` 是**抑制开关**（`getenv(...)==nullptr` 才跑探针），非"探针开关" | `generate.cpp:3090` |
| 机制修正 B | 慢盘自动切 `mmap` 仅在**未显式给 `--ple-io`** 时发生；显式给了只 warning | `generate.cpp:3091-3110`（注释逐字：`Recommend, never force`） |
| **#1733 落地核实** | **已 ported**，且实测生效 | `telemetry.py:191-229` 的 `_hops()` / `link()`；`/metrics` 实读 `"gpu_pcie_gen":3 "gpu_pcie_width":16` -- 正是我们诊断的 **Gen3 x16** |
| **#1732 落地核实** | **已 ported** | `prefill.cpp:1867` 的 `arm_cpu_share()` 被 `#if !defined(STRATA_USE_HIP) && !defined(STRATA_HIP_GFX906)` 包住 => gfx906 不走 CUDA 分支 |
| **#1731 落地核实** | **已 ported** | Niko1221 回复逐字，sparkline floor |
| **#1734 速率半** | **未采纳**（维护者选择"不填"而非任一我们给的选项） | 0.1.42 `_Amd.read()` 仍无 `pcie_rx_mb`/`pcie_tx_mb`；只补了 `pcie_path` |
| **#1735 name 一致性** | **上游未采纳，但本机已有补丁在生产运行** | 生产容器 `telemetry.py:167-182` 是 `serve-telemetry.py.patched` 覆写，已实现容量一致性；`/metrics` 实读 `"gpu_name": "Radeon Instinct MI50 32GB"`（FRU 原串是 `...16GB`） |

### 7.6 落账动作

- register：`P55`/`P56`/`P59`/`P60` 状态更新（见 §8）
- `W713_PLAN.md` §6.1 第 49 条 + §6.4 #1 关闭
- `mem_slim.py` 走技能入口刷新注入件


> **[BAN 归一说明 · 2026-10-11]** 本件属"活跃交付件"，已按项目禁用码位表（见 `W750_MASTER_PLAN.md` 第 0.5.7 节）做 **ASCII 归一**，映射：`U+2192`->`->` · `U+21D2`->`=>` · `U+2026`->`...` · `U+0394`->`delta` · `U+00D7`->`x` · `U+2014`->`--` · `U+2605`->`命中`/`*` · `U+2460-U+2469`->`(1)-(10)` · `U+2705`->`[OK]` · `U+26A0`->`[!]`。
> **引文处语义一字未改**，原文形态可回溯：改前副本 `deploy/tmp/_w21_bak/`（改前 md5 见件尾注）。
> 改前 md5 = `68b30b7209a3f72ad3de48378da90d14`（字节 13334）。
