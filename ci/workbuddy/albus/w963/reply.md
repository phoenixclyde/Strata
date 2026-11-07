**先答你问的那句：昨天最高 803.7 tok/s（61,246 token，11-03 23:53），今天最高 804.1（60,330 token，11-04 04:47）——同一权重，同一水平，没有掉。**

## 一、生产容器（8 字段）

| # | 项 | 值 |
|---|---|---|
| 1 | 容器 / 镜像 | `4f387a12e84b` / `strata-gfx906:0.2.10-101`（image `5267df6dbdeb`） |
| 2 | 运行中引擎 | `ae085365441381c438b56bcabcccf450`，42,924,432 B，`strata 0.1.56` |
| 3 | **config** | md5 `24d66f6a86d7b75f58015efa38d462d2`；exe=`/data/bin/strata-0.1.56`；**args 33 条**；**env 9 条** |
| 3a | args 明细 | `--pack /data/packs/ud-q4_k_xl` `--native …UD-Q4_K_XL-00001-of-00004.gguf` `--expert-profile /src/data/expert-profile.bin` `--expert-cache auto` `--pcie-frac 0.20` `--spec 4` `--spec-min-p 0.70` `--mtp /data/mtp/rt` `--max-context 262144` `--kv k8v4` `--prefill auto:16384` `--prompt-cache-every 8192` `--expert-profile-save /data/profiles/q4kxl-learned.bin` `--conversation-cache-mib 4096` `--vision` `--mtp-window 8192` `--vram-reserve-mib 832` |
| 3b | env 明细 | `HSA_OVERRIDE_GFX_VERSION=9.0.6` `STRATA_PREFILL_CPU_SHARE=auto` `STRATA_PREFILL_CPU_SHARE_MAX=3072` `STRATA_RESIDENT_HEADROOM_GIB=0.5` `STRATA_ROCBLAS_TUNING=/data/gfx906-rocblas-5.7.0.txt` `STRATA_GFX906_TUNED=1` `STRATA_CKPT_MOVE_PARK=1` `STRATA_DECODE_TIMING=1` `STRATA_SPEC_DEPTH=1` |
| 4 | 健康 | `/health` status=ok、`loaded:true`、restarts=0、StartedAt `2026-11-04T12:48:56Z`、max_context 262144 |
| 5 | 资源隔离 | `ulimit -l = unlimited`、`VmLck 28,125,140 kB` |
| 6 | 显存布局 | `expert cache 7463 slots / 21.79 GiB`、`borrows 2606 (7.62 GiB)`、`VRAM free 882 MiB` |
| 7 | 回滚件 | 容器 `strata166-407.pre-210`、引擎 `strata-0.1.55w`、`ci/strata-ci rollback --exe strata-0.1.55w --apply` |
| 8 | 本轮改动 | 部署分支**零**；disk = build = running 三方一致（`ae085365…`）；实验分支 `exp/R90-080` 2 提交未合 |

## 二、主线

`gfx906/mi50 @ 55a1acd4` · tag `mi50-0.2.10-r30` · 上游 `ffa80d73` · 落后 0 / 领先 39 · 工作树脏 0 行。

## 三、本次落生产

改动 **零**；回滚命令 `cp /data/strata-huihui-ud-iq4_xs.json.bak_w941 …/strata-huihui-ud-iq4_xs.json && docker restart strata166-407`；本轮为测量重启 **3 次**（chunk 两臂 + 热态尝试），停机 **≈14 分钟**。

## 四、进度 + 队列

**176 条 / 已结 101 / 57.4%**；死块池 0/28。队列：**W965 重做**（热态两臂，需换启动方式）→ R88-量 → R86-A/B → R87 → R46 → R91。

---

## 一、昨天 vs 今天（按 engine-start 时间归属）

| 时间 | prompt | tok/s |
|---|---:|---:|
| **11-03 23:53** | **61,246** | **803.7** |
| 11-03 17:19 | 61,246 | 803.3 / 799.1 |
| 11-03 17:06 | 30,588 | 796.4 |
| **11-04 04:47** | **60,330** | **804.1** |
| 11-04 04:47 | 60,008 | 800.2 |
| 11-04 | 130,105 | 789.6 |
| 11-04 | 15,819 | 711.4 |

⇒ 你记的"800 好几"是对的，**今天也一样**。

## 二、我的 604 是**冷启动**，不是生产

我的 A/B 用 `generate`，容器加载完就读第一段 prompt ⇒ 专家缓存是初始态，第一段要付全部换入成本。

| prompt | 冷（我的 generate） | 热（W863 的 probe，丢弃一次 warm-up） |
|---:|---:|---:|
| ~1,200 | — | **946** |
| 2,047 | **604** | — |
| 2,468 | — | **1231** |
| 4,859 | — | **1294** |
| 9,707 | **704 / 774** | **1404** |
| 60,000 | **808** | — |

同长度**热态≈冷态 2×**。所以"掉到 600"是我把冷态当成了生产口径——这个错在我。

## 三、今天把 chunk 改成 16384 是对的（不是退步）

同一二进制、同一 9,706 token，只换 `--prefill`：

| 臂 | `--prefill` | 结果 |
|---|---|---:|
| P8 | `auto`（8192 上限，11-04 04:34 前的配置） | 13,780 ms → **704.36 tok/s** |
| P16 | `auto:16384`（现在的配置） | 12,530 ms → **774.59 tok/s** |

⇒ **+10%**，今天的改动是正收益。

## 四、连带要纠正的

`W960`/`W962` 里"0.8.0 慢 6% / 5%"是**冷态**数字，冷态里很大一块是**换入**，不等于 MMQ 内核差。热态两臂我这一轮试着跑（`W965`），但引擎的 `serve` 不接 `--port`（production 是 python wrapper 起的），容器直接打 usage 退出，端口拒连——脚本已中止、生产已恢复。下一轮换成 wrapper 或走 8090 默认端口重跑，才能给 0.8.0 一个公平结论。

## 五、顺带确认真的一条工具细节

引擎打印的 tok/s 是**按实际读入 token** 算的：`prompt 7606 tokens = 7576 reused + 30 read in 629 ms (47.7 tok/s)`，30/0.629 = 47.7 ⇒ 日志速率**不含复用**，可以直接拿来比。

产物：`deploy/W963_COLD_VS_WARM_CLARIFICATION.md`。
