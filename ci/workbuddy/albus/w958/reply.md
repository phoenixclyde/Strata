## 一、生产容器（8 字段）

| # | 项 | 值 |
|---|---|---|
| 1 | 容器 / 镜像 | `4f387a12e84b` / `strata-gfx906:0.2.10-101`（image `5267df6dbdeb`） |
| 2 | 运行中引擎 | `ae085365441381c438b56bcabcccf450`，42,924,432 B，`strata 0.1.56` |
| 3 | **config** | md5 `24d66f6a86d7b75f58015efa38d462d2`；exe=`/data/bin/strata-0.1.56`；**args 33 条**；**env 9 条** |
| 3a | args 明细 | `--pack /data/packs/ud-q4_k_xl` `--native …UD-Q4_K_XL-00001-of-00004.gguf` `--expert-profile /src/data/expert-profile.bin` `--expert-cache auto` `--pcie-frac 0.20` `--spec 4` `--spec-min-p 0.70` `--mtp /data/mtp/rt` `--max-context 262144` `--kv k8v4` `--prefill auto:16384` `--prompt-cache-every 8192` `--expert-profile-save /data/profiles/q4kxl-learned.bin` `--conversation-cache-mib 4096` `--vision` `--mtp-window 8192` `--vram-reserve-mib 832` |
| 3b | env 明细 | `HSA_OVERRIDE_GFX_VERSION=9.0.6` `STRATA_PREFILL_CPU_SHARE=auto` `STRATA_PREFILL_CPU_SHARE_MAX=3072` `STRATA_RESIDENT_HEADROOM_GIB=0.5` `STRATA_ROCBLAS_TUNING=/data/gfx906-rocblas-5.7.0.txt` `STRATA_GFX906_TUNED=1` `STRATA_CKPT_MOVE_PARK=1` `STRATA_DECODE_TIMING=1` `STRATA_SPEC_DEPTH=1` |
| 4 | 健康 | `/health` status=ok、`loaded:true`、restarts=0、StartedAt `2026-11-04T10:54:44Z`、max_context 262144 |
| 5 | 资源隔离 | `ulimit -l = unlimited`、`VmLck 28,125,140 kB` |
| 6 | 显存布局 | `expert cache 7463 slots / 21.79 GiB`、`borrows 2606 (7.62 GiB)`、`VRAM free 882 MiB` |
| 7 | 回滚件 | 容器 `strata166-407.pre-210`、引擎 `strata-0.1.55w`、`ci/strata-ci rollback --exe strata-0.1.55w --apply` |
| 8 | 本轮改动 | 部署分支**零**；disk = build = running 三方一致（`ae085365…`）；实验分支 `exp/R90-080` 仍 `999b9121`（未合） |

## 二、主线

`gfx906/mi50 @ 55a1acd4` · tag `mi50-0.2.10-r30` · 上游 `ffa80d73` · 落后 0 / 领先 39 · 工作树脏 0 行。

## 三、本次落生产

改动 **零**；回滚命令 `cp /data/strata-huihui-ud-iq4_xs.json.bak_w941 …/strata-huihui-ud-iq4_xs.json && docker restart strata166-407`；本轮为测量重启 **3 次**（A1/A2/B1，每次 ≈4.5 分钟，脚本自动恢复），累计停机 **≈13 分钟**。

## 四、进度 + 队列

**176 条 / 已结 101 / 57.4%**；主线 148 / 101 / 68.2%；死块池 0/28。
队列：**R90-S4 第 3 轮**（先找出使 A 可复现的配置 → 测 KL 地板 → A/B 的 KL + 六长度档吞吐）→ R88-量 → R86-A/B → R87 → R88-实现 → R46 → R91 → R93 → R72 → R81 → R79 → R80 → R63/R60/R64 → R49 → R50 → R30′

---

## 结论：**生产件自己就不复现，"逐位"判据作废**

一次停服里跑了三次：A1、A2（都是 0.4.1 生产件）、B1（0.8.0 移植版），同 prompt、同 args。

| 对照 | 相同前缀 | 全同位置 |
|---|---:|---:|
| **A1 vs A2（同一二进制）** | **3** | **7 / 64** |
| A1 vs B1（跨版本） | 7 | 7 / 64 |
| **B1 vs 上一轮的 B（跨会话）** | — | **64 / 64** |

```
A1 : 248045 271 248045 487 198 262 328  846  763 328
A2 : 248045 271 248045 271 248045 271 248045 ...        ← 第 4 个就分叉
B1 : 248045 271 248045 487 198 262 328 1666 41882 763
B  : 248045 271 248045 487 198 262 328 1666 41882 763   ← 与 B1 逐字相同
```

⇒ 上一轮那个"前缀 7"**落在 A 自己的噪声里**，用它判升级是无效测量。而且**"可复现"的一方是待升级的 0.8.0**。

## 原因不是猜出来的，源码里写着

`src/program/generate.cpp:12706`：

> "**Not bit-exact run to run**: which window first computes a swapped-in expert on the GPU (**which rounds differently from the CPU**) depends on when its copy lands."

77 GB 模型塞 32 GB 卡，换入换出是常态：三次跑分别换入 **1436 / 576 / 1372** 个专家。

**但这条解释不了"B 为什么稳定"**——B1 也换入 1372 个、也开 adaptive、也开 rocBLAS tuning。待查假设按成本排序：
① rocBLAS 运行期按计时选解（两臂日志都有 `tuning enabled`）；② 换入序列；③ 我们的适配恰好修掉某个竞争。

## 判据改写（已写回 `W956 §9` 与账本）

"argmax/token 相同"在 0.4.1 上不成立，不能用来验收升级。升级只能验收两件事：

- **性能**：六长度档 A/B，`|Δ| ≥ 2×CV`，decode 只守不劣化；
- **质量**：对**金标**比 KL/top-1（不是两臂互比），且**先测噪声地板**——同二进制两次的 KL 若不是 0，就以它为门槛。

质量测量必须走 **serve + `STRATA_DUMP_FIRST_LOGITS`**（`generate.cpp:18572` 的 serve 分支）；generate 的 native pack 不写 dump。

## 下一步（顺序改了）

① 找确定性配置：A 跑两次，`--adapt-async 0` + 固定 rocBLAS 表/`--rocblas-tuning 0`，看能否 64/64；
② 该配置下测 **A vs A 的 KL 地板**（`W913` 曾得 0.0000，可判）；
③ A vs B 的 KL + top-1（`KL ≤ 0.005`、top-1 ≥ 99%）；
④ 六长度档吞吐 A/B（真实文本）。

产物：`deploy/W958_DETERMINISM_CONTROL.md`；账本 R90 仍 **INFLIGHT**；结案台账 38/38。
