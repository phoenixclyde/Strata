**一、生产容器（8 字段）**

| # | 项 | 值 |
|---|---|---|
| 1 | 容器 / 镜像 | `4f387a12e84b` / `strata-gfx906:0.2.10-101`（image `5267df6dbdeb`） |
| 2 | 运行中引擎 | `eea5ea3749ad54b124330386605a18bc`，44,908,992 B（strata 0.1.56，v0.9.0） |
| 3 | config | md5 `e62685e6ff21d9e2b60c1cd622fd5a67`；exe=`/data/bin/strata-0.1.56-090`；args 37；env 9 |
| 3a | args 明细 | `--pack /data/packs/ud-q4_k_xl --native …/unsloth-UD-Q4_K_XL-00001-of-00004.gguf --expert-profile /src/data/expert-profile.bin --expert-cache auto --pcie-frac 0.20 --spec 4 --spec-min-p 0.70 --mtp /data/mtp/rt --max-context 262144 --kv k8v4 --prefill auto:16384 --prompt-cache-every 8192 --expert-profile-save /data/profiles/q4kxl-learned.bin --conversation-cache-mib 4096 --vision --mtp-window 8192 --vram-reserve-mib 832 --ple-io mmap --pool-workers 10` |
| 3b | env 明细 | `HSA_OVERRIDE_GFX_VERSION` `STRATA_CKPT_MOVE_PARK` `STRATA_DECODE_TIMING` `STRATA_GFX906_TUNED` `STRATA_PREFILL_CPU_SHARE` `STRATA_PREFILL_CPU_SHARE_MAX` `STRATA_PREFILL_TIMING` `STRATA_ROCBLAS_TUNING` `STRATA_SPEC_DEPTH` |
| 4 | 健康 | `/health` ok、`loaded:true`、restarts=0、StartedAt 2026-11-05T11:58:52Z |
| 5 | 资源隔离 | `ulimit -l` = unlimited；`VmLck`: 0 kB |
| 6 | 显存布局 | expert cache 7463 slots / 21.79 GiB、borrows 2606（7.62 GiB）、882 MiB of VRAM free |
| 7 | 回滚件 | `strata-0.1.56-080`；`cp /data/strata-huihui-ud-iq4_xs.json.bak_w976 /data/strata-huihui-ud-iq4_xs.json` + `docker restart strata166-407` |
| 8 | 本轮改动 | 生产零改动、零重启；disk = build = running = `eea5ea37…` 三方一致 |

**二、主线**

gfx906/mi50 @ 20fca64a · tag `mi50-0.2.10-r32-13-g20fca64a` · 落后 0 / 领先 0 · 上游 `ffa80d73` · 工作树脏 0 行 · 远端一致（API：`20fca64ad3cc`）。

**三、本次落生产**

改动 0；重启 0 次；停机 0；回滚件未用。代码面本轮 2 个提交（`c43ffc98` 5 文件 +432/−12；`20fca64a` 1 文件 +9/−1），共 19 个提交推送（`5f73cd15..20fca64a`）；本轮这轮只动 `deploy/`（非 git 面）。

**四、进度 + 队列**

212 条 / 已结 136 / 64.2%；主线 184 / 136；死块池 0/28。
队列：R95 → R86（仅 down，条件启动）→ R94 → R91 → R89 → R46 → R49 → R50。

---

## 这轮问的：那些内容进方案了吗

**没有全进。** 上一轮的六通道表与举一反三，只有两句落进了 §6.5：

| 上一轮报告的内容 | 上轮是否进 §6.5 | 现在 |
|---|---|---|
| C4 融合 N/A（`prefill.cpp:5300` 单次 1280 行） | ✅ 进了（作为 R96 N/A） | — |
| C6 混合分派解散（w32 全胜） | ✅ 进了（作为 R97 解散） | — |
| C1 权重上传 / C2 `moe_mmq.cu:498` / C3 `block_q8_1_mmq` / C5 验收清单 | ❌ 只在 `docs/W1003_PORT_DECISION.md` 与 `PORT_STATUS.md`，**方案里一个字没有** | 已补 |
| 尺寸账（Q5_1 1,228,800 B 中性；Q8_0 1,740,800→1,781,760 +2.3%） | ❌ 没进 | 已补 |
| 举一反三 ①mx 的 `use_w32` 阈值不可照抄 | ❌ 没进 | 已补 |
| 举一反三 ②上游两笔融合对 prefill 无效 | ✅（即 R96 N/A） | — |
| 举一反三 ③dequant/wait copy 比 down 大 3–5 倍 | ❌ 我上轮只写了「归 R95」，等于把优先级写没了 | 已补，写成可对照的量级 |

已落地的动作：

1. `deploy/W832_OPT_PLAN_V2.md` 追加 **§6.5 补记 · W1003-b**：R86 的六通道执行落点（含 file:line）+ 尺寸账 + 举一反三三条（第 3 条写成「dequant/wait copy 8–18% / 7–15% 是 down repack −2.6%~−3.3% 的 3–5 倍，R86 立项条件是 R95 之后」）。六通道放在 §6.5 只是**执行落点**，条目定义仍在 §6.2「新21」，不新增 ID。
2. `PROGRESS.tsv`：P279（三条通道与差距）由 OPEN → **DONE**，note 里记六通道与尺寸账 ⇒ 212 / 136 / **64.2%**。
3. 同步 166 并逐字节校验：`W832` md5 `dd27414f46ab…`、`PROGRESS.tsv` md5 `f98e27c3e091…`，双侧一致（`mirror_check` PASS）。
4. `plan_lint` PASS（未登记 0 份、未结全在方案里、68 个 R 号全有账）。
