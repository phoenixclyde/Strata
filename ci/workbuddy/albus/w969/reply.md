**600 / 800 / 500 是三个口径，不是三个结论。** 我用同一个模型把它们全对上了：`t ≈ 1.7 s + n/822`。
长档 804 是真的（昨天 803.7，同一权重），短档 ~525 也是真的，而 946–1404 那个数是**长度阶梯里带前缀复用**（分母只算"读入"的 token），不能当冷读速率。我前几轮把它们混着报，这是错的。

## 一、生产容器（8 字段）

| # | 项 | 值 |
|---|---|---|
| 1 | 容器 / 镜像 | `4f387a12e84b` / `strata-gfx906:0.2.10-101`（image `5267df6dbdeb`） |
| 2 | 运行中引擎 | `ae085365441381c438b56bcabcccf450`，42,924,432 B，`strata 0.1.56` |
| 3 | **config** | md5 `24d66f6a86d7b75f58015efa38d462d2`；exe=`/data/bin/strata-0.1.56`；**args 33 条**；**env 9 条** |
| 3a | args 明细 | `--pack /data/packs/ud-q4_k_xl` `--native …UD-Q4_K_XL-00001-of-00004.gguf` `--expert-profile /src/data/expert-profile.bin` `--expert-cache auto` `--pcie-frac 0.20` `--spec 4` `--spec-min-p 0.70` `--mtp /data/mtp/rt` `--max-context 262144` `--kv k8v4` `--prefill auto:16384` `--prompt-cache-every 8192` `--expert-profile-save /data/profiles/q4kxl-learned.bin` `--conversation-cache-mib 4096` `--vision` `--mtp-window 8192` `--vram-reserve-mib 832` |
| 3b | env 明细 | `HSA_OVERRIDE_GFX_VERSION=9.0.6` `STRATA_PREFILL_CPU_SHARE=auto` `STRATA_PREFILL_CPU_SHARE_MAX=3072` `STRATA_RESIDENT_HEADROOM_GIB=0.5` `STRATA_ROCBLAS_TUNING=/data/gfx906-rocblas-5.7.0.txt` `STRATA_GFX906_TUNED=1` `STRATA_CKPT_MOVE_PARK=1` `STRATA_DECODE_TIMING=1` `STRATA_SPEC_DEPTH=1` |
| 4 | 健康 | `/health` status=ok、`loaded:true`、restarts=0、StartedAt `2026-11-04T13:28:15Z`、max_context 262144 |
| 5 | 资源隔离 | `ulimit -l = unlimited`、`VmLck 28,125,140 kB` |
| 6 | 显存布局 | `expert cache 7463 slots / 21.79 GiB`、`borrows 2606 (7.62 GiB)`、`VRAM free 882 MiB` |
| 7 | 回滚件 | 容器 `strata166-407.pre-210`、引擎 `strata-0.1.55w`、`ci/strata-ci rollback --exe strata-0.1.55w --apply` |
| 8 | 本轮改动 | 部署分支**零**；disk = build = running 三方一致（`ae085365…`）；无遗留测试容器 |

## 二、主线

`gfx906/mi50 @ 55a1acd4` · tag `mi50-0.2.10-r30` · 上游 `ffa80d73` · 落后 0 / 领先 39 · 工作树脏 0 行。

## 三、本次落生产

改动 **零**；回滚命令 `cp /data/strata-huihui-ud-iq4_xs.json.bak_w941 …/strata-huihui-ud-iq4_xs.json && docker restart strata166-407`；本轮重启 **1 次**（W968 的 `auto` 对照），停机 **≈6 分钟**；其余测量全部走在线服务或用 wrapper 起的临时容器。

## 四、进度 + 队列

**176 条 / 已结 101 / 57.4%**；死块池 0/28。
队列：**R88-量**（那 1.7 s 固定成本）→ R86-A/B → R87 → R46 → R91 → R93 → R72 → R81 → R79 → R80 → R63/R60/R64。

---

## 一、全部读数按口径归位（同一台机、同一权重 `ud-q4_k_xl`）

| 口径 | 条件 | prompt | tok/s |
|---|---|---|---:|
| **冷读 · 长**（生产稳态） | `cached=0` | 60,330 / 61,246(昨) / 130,105 / 15,819 | **804.1 / 803.7 / 789.6 / 711.4** |
| **冷读 · 短** | `cached=0` | 2,353 | **~525**（516 / 546 / 519，现场发 3 条不同 prompt） |
| | generate 冷启动 | 2,047 | 604 |
| **热读（前缀命中）** | `cached≈n-5` | 2,353 | 0.2 s |
| **长度阶梯 + 前缀复用** | `W863` 的探针 | 1,242 / 2,468 / 9,707 | 946 / 1231 / 1404 |

**关键**：引擎打印的 tok/s = **实际读入 token / 时间**。日志里 `prompt 1915 tokens = 1910 reused + 5 read in 214 ms (23.4 tok/s)` 就是证明——
D 那一栏的 1404 里，大量 token 是**复用跳过**的，分母只算"读"的那部分，所以它偏高。

## 二、一个模型把冷读全对上

```
t ≈ 1.7 s + n / 822
```

| n | 预测 | 实测 |
|---:|---:|---:|
| 2,353 | 4.6 s | 4.41–4.58 s |
| 15,819 | 20.9 s | 22.24 s |
| 60,330 | 75.1 s | 75.03 s |
| 130,105 | 160.0 s | 164.8 s |

⇒ **每段冷读有约 1.7 s 的固定成本**（首层专家竞技场 bring-up / 首块 staging）：2.3K 时占 38%，60K 时只占 2%。
"短 prompt 500、长 prompt 800"就是这 1.7 s 摊薄的结果。

## 三、逐个排除（谁都不是原因）

| 嫌疑 | 实验 | 结果 |
|---|---|---|
| `--prefill auto` vs `auto:16384` | 同二进制同 2K prompt | 524 vs 503（2K）；9.7K 时 16384 反而 **+10%**（775 vs 704） |
| 引擎版本 0.1.56 vs 回滚 0.1.55w | 同探针 | **503 vs 506** |
| 上游 0.8.0 vs 0.4.1 | 同探针 + 反汇编 | **497 vs 503**；J=64 内核 **23,164 vs 23,168 B**，sgpr 44 / vgpr 128 / spill 0 **全同** |
| GPU 降频 | 冷读时采 `sclk` | **1725 MHz**（上限 1746），满血 |
| `--resident-budget-gib` 丢失 | 765 次启动的配置史 | 10-11 就去掉了，**远早于 11-01** |

## 四、所以"到底多少"的答案

1. **长 prompt 的 800 是真的，今天仍在**（804.1 @60,330；昨天 803.7 @61,246）。
2. **短 prompt 的 500 也是真的**（2,353 token 冷读 ≈525）。
3. **946–1404 是带前缀复用的口径**，不是冷读速率——我前几轮把它当生产速率引用，是错的，已在 `W969` 更正。
4. **0.8.0 与 0.4.1 在代码级与实测上等价**（详见 `W966`），可以紧跟上游。

## 五、真正值钱的靶心

模型的 **1.7 s 固定成本**：首轮对话 TTFT 里约 1.7 s 是纯开销，且短 prompt 只跑到 525 tok/s。
这正好是 `R88`（异步分阶段拷贝 / wait-copy 相位）要吃掉的部分，和 `W853` 当年"wait copy 让 GPU 空转"的账对得上。
⇒ 继续在 0.4.1/0.8.0 之间比来比去，收益不如把 R88 做掉。

产物：`deploy/W969_UNIFIED_PREFILL_REGIMES.md`（口径表 + 模型 + 排除清单）、`W966_CODE_LEVEL_VERDICT.md`（内核级比对）；结案台账 42/42。
