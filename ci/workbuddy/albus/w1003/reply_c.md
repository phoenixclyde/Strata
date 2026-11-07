# W1003-c 收尾

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

gfx906/mi50 @ 2d07550f · tag `mi50-0.2.10-r32-14-g2d07550f` · 落后 0 / 领先 0 · 上游 `ffa80d73` · 工作树脏 0 行 · 远端一致（API：`2d07550fd4af`）。

**三、本次落生产**

改动 0；重启 0 次；停机 0；回滚件未用。代码面 1 个提交 `2d07550f`（`docs/W1003_PORT_DECISION.md` +3 行，只给六通道贴子号，不动引擎）；`deploy/` 与 `tools/plan_lint.py` 不在 git 面。

**四、进度 + 队列**

219 条 / 已结 139 / 63.5%；主线 184 / 139；死块池 0/28。
队列：R95 → R86（仅 down，条件启动）→ R94 → R91 → R89 → R46 → R49 → R50。

---

## 号在这里

| 号 | 内容 | 状态 | 落点 |
|---|---|---|---|
| **R86-C1** | 权重上传路径的 GPU 侧 repack（arena 装载一次，不进热路径） | OPEN | `W832 §6.5 补记` |
| **R86-C2** | `Context::run` 三路分派 + `expert_stride`→`repack_gcn_nbytes` + `Product.layout` | OPEN | 同上 |
| **R86-C3** | `block_q8_1_mmq` 尺寸/偏移断言（128 值 / 144 B、DS4） | PARTIAL | 同上 |
| **R86-C4** | gate/up + GLU 融合（上游 #31188） | NA | 同上（`prefill.cpp:5300` 单次 1280 行） |
| **R86-C5** | 验收链：逐位 + 六长度档 + 2×CV + KL + 灰度 + 回滚 | OPEN | 同上 |
| **R86-C6** | 按 `expert_bounds` 分段混合分派 | WITHDRAWN（计 0） | 同上 |
| **P289** | 六通道落点定稿并编号这件事本身 | DONE | `PROGRESS.tsv` |
| **P290** | 举一反三三条写死（`use_w32` 阈值 / 上游融合 / 性价比 3–5 倍） | DONE | `PROGRESS.tsv` |

## 上一版为什么没有号

我在 §6.5 写了一张**没有 ID 列**的表，前面还留了一句「本节不新立条目，免得队列里长出没有账本的 ID」——这句话是这次缺陷的根。删掉了，改成按号登记。

同时查出第二处更硬的：**R86 本体（`PROGRESS` 那行）还是旧口径**——写「88.6% 专家字节」「mx +84%」「本模型 +11% prefill」，与 W1003 三臂实测（gu 必亏 1.0–3.9×、down-only 端到端 −2.6~−3.3%）冲突。已改判据并加更正注。
