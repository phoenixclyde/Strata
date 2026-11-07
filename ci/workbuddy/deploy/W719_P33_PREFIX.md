# W719 ---- P33 `strata_prefix`（pin=N）：契约确认 + 实测无增量 + P31 生产参数复证

- 日期：2026-10-09 19:38 - 19:41（本机时间）
- 缘起：推进 §6.2 剩下的 P33（register scope = `REQ`，即**请求级**，理论上零成本、无需重启）。
- **结论先说**：① **契约确认**（请求体**顶层** `strata_prefix`，三种写法）；② **语义确认**（pin 的 checkpoint
  永不被 retention 驱逐）；③ **实测无增量** ---- 长文档 4 轮追问，带 pin 与不带 pin 的 `prompt_ms` 差在噪声内，
  因为**该 4 轮窗口内 `evictions=0`**（pin 只在真驱逐时才有用）；④ **副产品**：同一实测在 huihui 权重 + 生产参数下
  **复证了 P31**（轮 1 冷预填 11,785 ms -> 轮 2-4 826/1207/946 ms，**-93% ~ -90%**）。

---

## 1 契约：怎么用（此前未记录，本波补齐）

| 项 | 值 |
|---|---|
| 字段位置 | 请求体 **顶层**：`{"model": ..., "messages": [...], "strata_prefix": {...}}` |
| 三种写法 | `{"messages": K}`（前 K 条消息）· `{"message": I, "chars": N}`（第 I 条消息的前 N 字符）· `{"tokens": N}` |
| 解析 | serve 的 `Service.resolve_prefix`（`server.py:3289`）把它解析成 `{"tokens": N}`，**即引擎的 `pin=N`** |
| 链路 | `server.py:3284` 写回 `req["strata_prefix"]`；`server.py:3961` 是 `svc.run(ids, ..., req, ...)` => **`req` 就是 `sampling`** => `sampling_keys` 能读到它（`server.py:975`） |
| 前置 | `--prompt-cache >= 3`（我们默认 **6** ✓）、该请求非 `ckpt=0`、`N` 必须**短于 prompt** |
| 校验强度 | **强**：非法值 => **HTTP 400** + 明确消息；而同类字段 `strata_tune` 的非法值**静默忽略** |
| 失败模式 | 解析不出可用前缀时**不拒绝请求**（只打日志：`strata_prefix ... ignored: ...`） |

**探针定层级的证据**（本机直连 166:8090）：

| 探针 | HTTP | 说明 |
|---|---|---|
| T1 顶层 `strata_prefix: {"bogus": 1}` | **400** | `invalid_request_error` + `strata_prefix: {"messages": K} ... or {"tokens": N}` => **字段在顶层** |
| T2 `sampling.strata_prefix: {"bogus": 1}` | 200 | 被忽略（不是识别位置） |
| T3 顶层 `{"tokens": 99999}`（> prompt） | 200 | serve stdout：`strata_prefix tokens=99999 ignored: it leaves no usable prefix of the 53-token prompt` |
| T4 顶层 `strata_tune: {"pcie_frac": "x"}` | 200 | 静默忽略（对照） |

---

## 2 语义（源码原文，`generate.cpp:8931-8934`）

> `pin=N`: the first N prompt tokens are a shared read-only prefix (a long document that many short queries follow).
> The prompt is read in two parts at N, **the checkpoint there is PINNED (retention never evicts it, a parked
> conversation holding it stays parked)** and **a later request that resumes from it does not park the branch it
> leaves: N queries cost one prefix, not N.**

=> **一句话**：它保护的是"**共享前缀不被驱逐**"，收益形式是"**N 次查询只付 1 个前缀**"。

---

## 3 实测：无增量（因为预算是够的）

**设计**：长文档 300 条约 **4,877 token**（单独作为 messages[0]）+ 4 轮追问；
臂 A **每轮带** `strata_prefix: {"messages": 1}`，臂 B 不带（两臂用**不同文档内容**，避免互相命中缓存）。

| 轮 | 臂 A（带 pin）`prompt_ms` | 臂 B（不带）`prompt_ms` | A `cached_tokens` | B `cached_tokens` |
|---|---|---|---|---|
| 1（冷） | 11,784.8 | 11,419.5 | 0 | 0 |
| 2 | 825.7 | 667.4 | 4,872 / 4,903 | 4,872 / 4,903 |
| 3 | 1,207.0 | 775.0 | 4,898 / 4,929 | 4,898 / 4,929 |
| 4 | 945.9 | 1,098.7 | 4,924 / 4,955 | 4,924 / 4,955 |

- 两臂轮 2-4 的降幅都 ~90%，**差在噪声内**（有快有慢，无系统性方向）。
- `cached_tokens` 两臂都 = `prompt_tokens - 31`（近全量复用）。

**机理**（为什么无增量）：pin 的作用点是 `generate.cpp:7278-7287` ---- `pin_flags` 只传进**选 victim 的函数**
（`... stamps, o.prompt_cache, tail_flags, pin_flags`）。**没有驱逐，pin 就没有作用面**。
本机**该窗口**日志 `evictions=0`（会话缓存 `--conversation-cache-mib 4096` 对"单会话长文档 + 4 轮"绰绰有余；
`parked` 计数只到 2-3、占用约 0.65-1.54 GB）。

=> **P33 的适用条件是：会话缓存吃紧、retention 开始驱逐**（那时 pin 保证共享前缀不被踢掉）。
在我们的预算与使用强度下，**P31 的会话缓存已经把事情做完了**。

---

## 4 副产品：P31 在生产参数下的复证（本波意外收获）

同一实测**恰好**是 P31 的一次生产级复证 ---- 而且此前 W713 B3 是在 **base 权重 + 临时容器**里测的，这次是
**huihui 权重 + 现役 `-407` + 生产参数**：

| 项 | 值 |
|---|---|
| 轮 1 冷预填 | **11,785 ms**（4,877 token，413.8 tok/s） |
| 轮 2 | **826 ms**（4,872 reused + 31 read） |
| 轮 3 | **1,207 ms**（4,898 reused + 31） |
| 轮 4 | **946 ms**（4,924 reused + 31） |
| 降幅 | **-93.0% / -89.8% / -92.0%** |

=> 与 W713 B3 的"追问 TTFT -88% ~ -90%"**一致**，且这次是在正式生产配置上取得的。

---

## 5 判定

| 项 | 结论 |
|---|---|
| register P33 | **保持 CANDIDATE**（请求级、零成本：不传即无影响）；evidence/verdict 更新为本波契约与实测 |
| verdict | 仅在会话缓存**吃紧并出现 `evictions`** 时才可能受益；本机 4096 MiB 预算下该 4 轮长文档 `evictions=0` => **该窗口内无增量**。**W735 更正**："预算够"不是恒真 ---- 4 槽占满后新 park 确实会驱逐，现役 `/metrics` 的 `conversation_cache.evictions` 已到 5（`slots:4 parked:4`），故 P33 的适用条件是"缓存吃紧"，本机只是**大多数窗口**不触发。register 仍保持 CANDIDATE（请求级、零成本、不传即无影响）|
| 实用建议 | 客户端若做"**一份长文档 + 大量短问**"且**同时有别的会话在抢缓存**，可传 `strata_prefix: {"messages": 1}`；单会话场景不必传 |
| 副作用 | 无（请求级；不改配置、不需重启）。register 已推 166，两侧 md5 一致 |

---

## 6 证据索引

| 件 | 位置 |
|---|---|
| 契约源码 | 容器内 `serve/server.py:975 / 3284 / 3289-3306`；`src/program/generate.cpp:8931-8934 / 7278-7287 / 9859-9867` |
| 层级探针 | 本波 T1-T4（本机直连 166:8090）；serve stdout 两条（400 + ignored） |
| 两臂实测 | 本报告 §3；原始读数见下表（引擎日志 `/data/strata-huihui-ud-iq4_xs.log` 行 744/750/757/764 与 771/779/786/793） |
| 会话缓存行 | 同日志行 749-792（`parked ... evictions=0`） |

> 过程脚本（本机）：`_p33recon / _p33src / _p33layer / _p33probe / _p33bench / _p33log / _p33trace / _p33reg.py`，
> 均在 `C:\Users\clyde\AppData\Local\Temp\`。
