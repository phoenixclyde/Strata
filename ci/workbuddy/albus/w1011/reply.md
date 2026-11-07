**一、生产容器（8 字段）**

| # | 项 | 值 |
|---|---|---|
| 1 | 容器 / 镜像 | `4f387a12e84b` / `strata-gfx906:0.2.10-101`（image `5267df6dbdeb`） |
| 2 | 运行中引擎 | `eea5ea3749ad54b124330386605a18bc`，44,908,992 B |
| 3 | config | md5 `e62685e6ff21d9e2b60c1cd622fd5a67`（**已确认与上一轮恢复后一致**）；exe=`/data/bin/strata-0.1.56-090`；args 37；env 9 |
| 3a | args 明细 | 未变（`--prefill auto:16384`、`--expert-cache auto`、`--ple-io mmap`、`--pool-workers 10` 等 37 项） |
| 3b | env 明细 | 未变（9 项；`CPU_SHARE_MAX=3072`） |
| 4 | 健康 | `/health` ok、`loaded:true`；StartedAt 2026-11-05T15:33:28Z；restarts=0（本轮未重启） |
| 5 | 资源隔离 | `ulimit -l` unlimited；`VmLck` 0 kB |
| 6 | 显存布局 | expert cache 7463 slots / 21.79 GiB、borrows 2606（7.62 GiB）、882 MiB of VRAM free（启动时值） |
| 7 | 回滚件 | `strata-0.1.56-080`；`cp /data/strata-huihui-ud-iq4_xs.json.bak_w976 /data/strata-huihui-ud-iq4_xs.json`（本轮未用） |
| 8 | 本轮改动 | 生产零改动、零重启；disk = build = running = `eea5ea37…` |

**二、主线** gfx906/mi50 @ c409936f · tag `mi50-0.2.10-r32-17-gc409936f` · 落后 0 / 领先 0 · 上游 `ffa80d73` · 工作树脏 0 行。
**三、本次落生产** 改动 0；重启 0 次；停机 0；代码面 0 提交（本轮只读源码与日志）。
**四、进度** 248 条 / 已结 168 / **67.7%**；队列 R95（建计划挪 issuer，需代码）→ R98 → R94 → R91 → R89 → R46。

---

## 一、`LAYER_MAJOR` 不是移植项，是现成开关 —— 但对我们没用

上一轮说"下一步查 LAYER_MAJOR"。查完：

- **代码在**：`prefill.cpp:6277` 起是完整实现，env 面 5 个（`LAYER_MAJOR` / `LM_TOKENS` / `LM_R` vram|host / `LM_FORCE` / `LM_MARGIN_MIB`）；`arch_defaults_test.cpp:590-594` 断言**单 GPU 与 HIP 构建默认关**。
- **但它赚的东西我们早就赚到了**：其注释逐字 *"every chunk streams every routed expert again… Expert traffic drops by ~S / 512"* —— 而我们的 chunk 是 **16384**（日志逐字 `prompt chunk auto: 16384 tokens, a 384-slot ring`）。一个 chunk 走完 48 层，每个被路由的专家**已经只 stage 一次**。**它用 VRAM 换来的一样东西，我们用 16384 的 chunk 已经换到了。**

## 二、于是四个负结果是同一件事

| 机制 | 它想省的 | 我们省不到的原因 |
|---|---|---|
| `ROUTED_STREAM`（R66） | 不拷没人路由的专家 | 1K 档 −7.6%；而我们 `wait copy` 只有 37 ms |
| `STREAM_MIN`（P128） | 改"每专家都流"的阈值 | 往小否、往大 −4~−20%；2K/16K 同走 stream-all |
| `LAYER_MAJOR` | 每专家每 super-chunk 只 stage 一次 | chunk 已是 16384 |
| `PREFILL_WARM` | 层间预热 | 默认开，且只对 <1024 的 chunk 生效 |

⇒ **R95 的"专家流式/预取"整条分支关闭**。这不是"又否了一个想法"，而是四条历史负结果终于有了同一个解释：**我们只 stage 一遍，所有省"重复 stage"的机制都没有可省的**。

## 三、剩下的 110 ms 在哪，以及为什么没有现成开关

`host grouping` = 主机每层建组计划（1.3–1.9 ms/层），它**本来就在计算流的关键路径上**，所以 2K 时暴露得多。要藏它，只能把**建计划**挪到 issuer 线程——现在挪的是 blob 拷贝，不是计划本身。**没有 env 能做这件事**，所以它是代码改动，进实验树，不进生产。

## 四、门

`plan_lint` / `pointer_lint` / `plan_retired` / `audit_index` / `kernel_curve` / `mirror` 六项全绿；六件权威件双侧逐字节一致。
