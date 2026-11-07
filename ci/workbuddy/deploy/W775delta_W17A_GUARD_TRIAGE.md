# W775delta W17a/W17c ---- 132(X) + 73(M) 条未登记开关的**守卫判定**

日期 2026-10-11 13:50 ｜ 源 = 0.1.42 镜像只读扫描产物（本地复用，**0 发车**）｜ 工作区 `D:/workbuddy_space/strata_ws/`

> 触发：`W17a`（132 条逐条守卫判定）+ `W17c`（M 面 73 条复核）。判据 = **读守卫上下文**，
> 不再用名字筛（`ROUTE_TAIL_SKIP` 已证名字筛会骗人：它落在多卡段里却单卡仍活）。

## 1 方法（可复现，0 发车）

输入三件（本波已归档，md5 与 `W17` 件一致）：`_w17_scan.txt`（二进制/源码 getenv 面）·
`_w17_stack.txt`（每个 `getenv` 的**最近外层 `#if` 守卫**）· `_w17_verdict.tsv`。
脚本 = `deploy/tmp/_w17a_triage.py`；输出 = 本件 + `deploy/tmp/_w17a.tsv`（205 行全表）。

**分类规则（显式，可审）**：运行期门按守卫原文 + 名字取 6 类；是否改答案按名字取 2 类（保守）。

## 2 X 桶（132 条）运行期门分布

| 门 | 条数 |
|---|---:|
| 无守卫（恒可达） | 111 |
| 有守卫（原文见列 G） | 18 |
| 本卡专属（开） | 3 |

**其中「本卡专属（开）」3 条**：`STRATA_HIP_ROUTER_FAST` `STRATA_MMVQ_WAVE` `STRATA_ROUTER_BLOCK`

## 3 M 桶（73 条）运行期门分布 ---- W17c 的答案

| 门 | 条数 |
|---|---:|
| 无守卫（恒可达） | 69 |
| 有守卫（原文见列 G） | 2 |
| 本卡专属（开） | 1 |
| 不可达：需 PLE 表(--ple-gguf/--ple-io) | 1 |

> **W17c 结论（据实收紧）**：M 桶 73 条里 **69 条「编译期无守卫」** ---- 即「名字像多卡」**不等于**「编译期被排除」。
> 这正是 `ROUTE_TAIL_SKIP` 的形态（文档/名字说 AMD 不适用，实际单卡仍活）。
> **但**：列 G 为空只说明**没有 `#if` 守卫**，**不等于没有运行期条件**（如 `o.peer_device < 0`、`o.replicas > 1`）。
> => M 桶**须逐条读运行期条件**才能定活/死；**名字筛与守卫栈都只能给上界**，不能当判决。

## 4 短名单（族有线索 + 可达 + 非改答案嫌疑）---- W17b 的靶

> **[!] 更正（2026-10-11，见 `W775delta_W17A_GUARD_RESOLVE.md`）**：本表 §5 那 20 条「有守卫（原文见列 G）」**已用 0.1.42 源码树逐条解析完**；短名单 **36 -> 44 条**（+9：`PF_OCC`/`PF_OCC_W`/`IO_PF_AHEAD`/`IO_PF_STAGE`/`READ_AHEAD`/`SESSION_BUFFERED`/`NO_ARENA_THP`/`PIN_GUARD`/`UNBUFFERED_LOAD`；-1：`SELECT_WMMA` 判改答案且机制是 RDNA4 WMMA；降级 1：`PF_PAD` 须搭 `PF_GEMM`）。**下列为解析前的那一版。**

**36 条**（按族）：

| 族 | 条数 | 例 |
|---|---:|---|
| prefill | 11 | `STRATA_PF_HCDOWN`, `STRATA_PF_STEP_SYNC`, `STRATA_PREFILL_CPU_SHARE_MAX`, `STRATA_PREFILL_EQUAL`, `STRATA_PRE |
| MTP | 9 | `STRATA_GR_DOWN_MAX4`, `STRATA_GR_V3`, `STRATA_MTP_BATCH`, `STRATA_MTP_BATCH_F16`, `STRATA_MTP_BATCH_RING`, `S |
| verify/commit | 5 | `STRATA_COMMIT_SYNC`, `STRATA_DF_BRANCH`, `STRATA_DF_PLE`, `STRATA_DF_QB_Q4`, `STRATA_VERIFY_DEBUG` |
| GDN | 5 | `STRATA_GDN_COMMIT_SPLIT`, `STRATA_GDN_CONVL2`, `STRATA_GDN_CONV_SERIAL`, `STRATA_GDN_REC_HEADS`, `STRATA_GDN_ |
| KV/IO | 4 | `STRATA_IO_THREADS`, `STRATA_KV_GROW_FLOOR`, `STRATA_KV_GROW_INIT`, `STRATA_KV_GROW_STEP` |
| 采样 | 1 | `STRATA_ARGMAX_MULTI` |
| 会话 | 1 | `STRATA_CACHE_MESSAGE_BOUNDARY` |

### 4.1 完整短名单

- `STRATA_ARGMAX_MULTI`  (采样; 无守卫（恒可达）)
- `STRATA_CACHE_MESSAGE_BOUNDARY`  (会话; 无守卫（恒可达）)
- `STRATA_COMMIT_SYNC`  (verify/commit; 无守卫（恒可达）)
- `STRATA_DF_BRANCH`  (verify/commit; 无守卫（恒可达）)
- `STRATA_DF_PLE`  (verify/commit; 无守卫（恒可达）)
- `STRATA_DF_QB_Q4`  (verify/commit; 无守卫（恒可达）)
- `STRATA_GDN_COMMIT_SPLIT`  (GDN; 无守卫（恒可达）)
- `STRATA_GDN_CONVL2`  (GDN; 无守卫（恒可达）)
- `STRATA_GDN_CONV_SERIAL`  (GDN; 无守卫（恒可达）)
- `STRATA_GDN_REC_HEADS`  (GDN; 无守卫（恒可达）)
- `STRATA_GDN_SPLIT`  (GDN; 无守卫（恒可达）)
- `STRATA_GR_DOWN_MAX4`  (MTP; 无守卫（恒可达）)
- `STRATA_GR_V3`  (MTP; 无守卫（恒可达）)
- `STRATA_IO_THREADS`  (KV/IO; 无守卫（恒可达）)
- `STRATA_KV_GROW_FLOOR`  (KV/IO; 无守卫（恒可达）)
- `STRATA_KV_GROW_INIT`  (KV/IO; 无守卫（恒可达）)
- `STRATA_KV_GROW_STEP`  (KV/IO; 无守卫（恒可达）)
- `STRATA_MTP_BATCH`  (MTP; 无守卫（恒可达）)
- `STRATA_MTP_BATCH_F16`  (MTP; 无守卫（恒可达）)
- `STRATA_MTP_BATCH_RING`  (MTP; 无守卫（恒可达）)
- `STRATA_MTP_CATCHUP_ALL`  (MTP; 无守卫（恒可达）)
- `STRATA_MTP_FULL_HEAD`  (MTP; 无守卫（恒可达）)
- `STRATA_MTP_PREFILL_SYNC`  (MTP; 无守卫（恒可达）)
- `STRATA_MTP_TOP2`  (MTP; 无守卫（恒可达）)
- `STRATA_PF_HCDOWN`  (prefill; 无守卫（恒可达）)
- `STRATA_PF_STEP_SYNC`  (prefill; 无守卫（恒可达）)
- `STRATA_PREFILL_CPU_SHARE_MAX`  (prefill; 无守卫（恒可达）)
- `STRATA_PREFILL_EQUAL`  (prefill; 无守卫（恒可达）)
- `STRATA_PREFILL_GROUP_GATHER`  (prefill; 无守卫（恒可达）)
- `STRATA_PREFILL_ISSUER`  (prefill; 无守卫（恒可达）)
- `STRATA_PREFILL_LEND_PCT`  (prefill; 无守卫（恒可达）)
- `STRATA_PREFILL_RING`  (prefill; 无守卫（恒可达）)
- `STRATA_PREFILL_STREAM_AHEAD`  (prefill; 无守卫（恒可达）)
- `STRATA_PREFILL_STREAM_MIN`  (prefill; 无守卫（恒可达）)
- `STRATA_SELECT_OLD`  (prefill; 无守卫（恒可达）)
- `STRATA_VERIFY_DEBUG`  (verify/commit; 无守卫（恒可达）)

## 5 需先读源码才能定的（守卫非空且非上述 5 类）

**18 条** ---- 逐条守卫原文在 `_w17a.tsv` 列 G；这类**不能用**在发车前，须先读那段 `#if`。

## 6 已判「不可达」与「本卡专属」的（X 桶 + M 桶，本机现役配置）

- **不可达：需 PLE 表(--ple-gguf/--ple-io)**（1）：`STRATA_REMOTE_SPIN`
- **本卡专属（开）**（4）：`STRATA_HIP_ROUTER_FAST` `STRATA_MMVQ_WAVE` `STRATA_ROUTER_BLOCK` `STRATA_ARENA_MMAP`

> 注：X 桶内**没有** PLE / 多卡 / q4_0 门（那些名在 M 桶或已登记），
> 故「不可达」类主要出现在 M 桶 ---- 这也是 W17c 与 W17a 的交集。

## 7 局限（必须随行）

1. 运行期门是**守卫文本 + 名字**的判读，**不是**逐条跑出来的；最终判据仍是发车实测。
2. 「是否改答案」用**保守名字表**，标「待判」不等于「不改答案」；改答案类发车前须配 `STRATA_LOGPOS` 门（`P51`）。
3. 守卫取的是**最近外层 `#if`**；条件里的运行期变量（如 `o.peer_device < 0`）需读源码语义才能定活/死。
4. 本件不覆盖同一 env 的多分支语义（`=0` / `=1` / 设值）。
5. **名字筛对 `*_DEBUG` 类会漏**（DIAG 正则只含 `DBG`，不含 `DEBUG`）---- 故短名单里仍可能混入纯诊断项，
   发车前须回源码确认该键是否只影响日志。

## 8 产物

- `_w17a.tsv`  (19046 B / `83e921793247637c1667a2b7fd966519`)
- `_w17_stack.txt`  (27775 B / `db989437f760a02ff8b261e76743ce6e`)
- `_w17_scan.txt`  (68439 B / `60717548ddb6902c581184fb5d847313`)

