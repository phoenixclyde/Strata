# W840 · 生产量化快照（接手首测）

时间：2026-10-31 17:29–17:36 CST　取数：16 6宿主 `python3 ~/strata166/tmp/state_q.py` + 两点法自测 + `verify_patches.sh`

## 1 一行结论

生产健康、门禁 17/17 PASS、部署物与构建产物 md5 同一；现场四个数字全部复核通过（显存 97.8%、缓存 7463 槽、
借用 1578 槽、预热 12.8 GB/s），**唯一需要更正的是 decode 的测法**：51 tok/s 是真的（两点法 51.1，n=1），
`state_q` 单点值是**整请求口径**（45.7）；一旦有并发长 prompt，单点会掉到 6.1。

## 2 量化表

| 项 | 实测值 | 取数方式 |
|---|---|---|
| 容器 | `strata166-407`，Up 28 min，started 17:02:55 CST，`unless-stopped` | docker inspect |
| 镜像 | `strata-gfx906:0.2.8p2`，id `a48890d4ecce…`，建于 10:43:04，6,972,473,163 B | docker inspect |
| 引擎 | `/data/bin/strata-0.1.54n3`，38,281,544 B（36.5 MiB），mtime 16:55 | ls -l |
| 部署 md5 | `21b50786a11ea4255ea0497357196077` | md5sum |
| 构建产物 md5 | `21b50786a11ea4255ea0497357196077`（`src028/build-028r/strata`） | 同串 ✓ |
| args / env | **33 / 6** | 配置 JSON |
| 显存 | **33.6 / 34.3 GB = 97.8%**（17:29 采样 33.6，17:31 采样 33.6） | rocm-smi |
| 专家缓存 | **7463 槽 / 21.79 GiB**（占显存 63.5%，3.0 MiB/槽） | 启动日志 |
| 提示路径借用 | **1578 槽 / 4.62 GiB**（占缓存 21.2%，3.0 MiB/槽） | 启动日志 |
| 预热 | 7463/7463 槽 in 1.8 s = **12820 MB/s**（另一处文档记 12739；差 0.6%，**不是**统计量，无 n 次样本） | 启动日志 |
| 自适应 tier | 413 轮 / 16511 次换入 / **46.9 ms per round**（累计 ≈19.4 s） | 启动日志 |
| `/health` | `ok`，loaded=true，max_context=262144 | HTTP |
| 配置 md5 | `34aca1a95e609d55ccfc5344da8c94a5`；`.bak-w839` = `0d67f258…`（不同 ✓） | md5sum |

## 3 速率（三种测法，别混用）

| 量 | 值 | 条件 |
|---|---|---|
| 纯解码 | **51.1 tok/s = 19.58 ms/tok** | 两点法（8 tok 与 264 tok 同一 prompt 相减，去掉 prefill/TTFT），启动后第二臂 |
| 单点 decode | 45.7 tok/s | `state_q` 128 tok 整请求墙钟，含该 prompt 的 prefill + TTFT |
| 被抢占样本 | 6.1 tok/s | 17:29 采样时容器内有一个 **118,150 token** 的请求正在 reading（GPU util 100%、prefill_mean 731） |
| prefill | **697 tok/s**（8858 tok / 12.72 s） | 全新 8.8k prompt，max_tokens=1 |

- 两点法第一臂（75.9）不可用：它是 17:31 那次 state_q 探针（已发 3 条请求）之后约 5 分钟的**冷启动**样本（8 tok 花 1.17 s）。**n=1**；`dn=134` 是两条请求 `completion_tokens` 之差的实测值（未假定恰好 8/264）。
- 118k 长 prompt 期间（17:29：`live.prompt_tokens=118150` 而 `totals.prompt_tokens=62` ⇒ 该请求尚未计入累计），探针整请求墙钟被压到 6.1 tok/s（≈12%）。**这解释了单次取样为何会莫名偏低**，不是引擎退化。
- 累计计数 `requests=6 / prompt_tokens=120,211`，其中 118,150 来自那一个长 prompt。

## 4 门禁（17 项全 PASS）

`W793 W776 W794 / TEL-PCIE×2 / WEB-UI×3 / W831×3 / W830-COMPAT / W837 / W839×3 / PROVENANCE` = 17。
关键三项：`W839 tree: apply_arch_defaults call site` OK、`W839 binary: entry linked` OK、`W839 deployed engine: entry linked` OK。

启动横幅两行齐全，数字自洽：
- `2 exact speed switches on by default: GDN_HEAD GFX906_ATTN_REDUCE12`
- `7 rounding-level recipe: GFX906_ATTN_QUERY_SWIZZLE GDN_PP HC_Q8 SELECT_SIMT ROUTE_TAIL_SKIP MMQ_KQ HIP_PROMPT_F16`
- 2 + 7 = 9，与「9 条 arch 变量由引擎自设」一致 ⇒ 入口真的在跑（不是树里有、二进制里没有）。

## 5 仓库状态

`166:~/strata166/gfx906` 分支 `gfx906/0.2.8-mi50`，head `9ac564f`，工作区 **clean**（`git status --porcelain` 空），
前三个 commit：`9ac564f` 设备探测追踪 / `1309b1d` 真正调用 apply_arch_defaults / `642de24` 每卡入口。

回滚件齐：配置 `.bak-w839`、二进制 `strata-0.1.54n2`（38,262,328 B）、镜像 `0.2.8p1`。

## 6 与现场记录的三处差异（都不影响结论）

1. 显存 33.6 / 97.8%，现场写 33.5 / 97.6% —— 属采样抖动（33.5–33.6 之间）。
2. decode 现场 51 tok/s 用两点法复核为 51.1（**n=1**），**站得住但只有一次**；`state_q` 的 45.7 是**整请求口径**（含该 prompt 的 prefill 与 TTFT），不是退化。§1 把 45.7 归给「并发长 prompt」是错的——并发污染只解释了 6.1 那一次。
3. 现场表里没有的两个新数：自适应 tier 413 轮 / 16511 换入 / 46.9 ms·轮（累计 19.4 s），以及 prefill 697 tok/s。

## 7 建议的下一步（未开工）

1. `STRATA_PCIE_FRAC_DEFAULT=auto`（P227）：唯一可能改 decode 的死块。需要一次停服（≈4 min 载入）+ A/B。
   注意：一旦在 `build-028r` 重建而暂不部署，`PROVENANCE` 门禁会因「部署物不再匹配新构建产物」变红，
   所以要么**同轮内构建→部署→门禁**一条龙，要么先把现产物另存。
2. `GDN_PP` 单臂 KL（P229，约 6 min/臂）：纯数值判定，不需要停服。
3. 把分支→同步→编译→部署→门禁串成一条命令（可先做，零风险）。
