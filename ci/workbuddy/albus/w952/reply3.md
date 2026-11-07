## 一、生产容器（8 字段）

| # | 项 | 值 |
|---|---|---|
| 1 | 容器 / 镜像 | `4f387a12e84b` / `strata-gfx906:0.2.10-101`（image `5267df6dbdeb`） |
| 2 | 运行中引擎 | `ae085365441381c438b56bcabcccf450`，42,924,432 B，`strata 0.1.56` |
| 3 | **config** | md5 `24d66f6a86d7b75f58015efa38d462d2`；exe=`/data/bin/strata-0.1.56`；**args 33 条**；**env 9 条** |
| 3a | args 明细 | `--pack /data/packs/ud-q4_k_xl` `--native …UD-Q4_K_XL-00001-of-00004.gguf` `--expert-profile /src/data/expert-profile.bin` `--expert-cache auto` `--pcie-frac 0.20` `--spec 4` `--spec-min-p 0.70` `--mtp /data/mtp/rt` `--max-context 262144` `--kv k8v4` `--prefill auto:16384` `--prompt-cache-every 8192` `--expert-profile-save /data/profiles/q4kxl-learned.bin` `--conversation-cache-mib 4096` `--vision` `--mtp-window 8192` `--vram-reserve-mib 832` |
| 3b | env 明细 | `HSA_OVERRIDE_GFX_VERSION=9.0.6` `STRATA_PREFILL_CPU_SHARE=auto` `STRATA_PREFILL_CPU_SHARE_MAX=3072` `STRATA_RESIDENT_HEADROOM_GIB=0.5` `STRATA_ROCBLAS_TUNING=/data/gfx906-rocblas-5.7.0.txt` `STRATA_GFX906_TUNED=1` `STRATA_CKPT_MOVE_PARK=1` `STRATA_DECODE_TIMING=1` `STRATA_SPEC_DEPTH=1` |
| 4 | 健康 | `/health` status=ok、`loaded:true`、restarts=0、StartedAt `2026-11-04T08:14:34Z`、max_context 262144 |
| 5 | 资源隔离 | `ulimit -l = unlimited`、`VmLck 28,125,140 kB` |
| 6 | 显存布局 | `expert cache 7463 slots / 21.79 GiB`、`borrows 2606 (7.62 GiB)`、`VRAM free 882 MiB` |
| 7 | 回滚件 | 容器 `strata166-407.pre-210`、引擎 `strata-0.1.55w`、`ci/strata-ci rollback --exe strata-0.1.55w --apply` |
| 8 | 本轮改动 | **零**；disk = build = running = `ae085365…` 三方一致 |

## 二、主线

`gfx906/mi50 @ 5f73cd15` · tag `mi50-0.2.10-r28` · 上游 `ffa80d73` · 落后 0 / 领先 37 · 工作树脏 0 行 · 与 origin 同点。

## 三、本次落生产

改动 **零**；回滚命令 `cp /data/strata-huihui-ud-iq4_xs.json.bak_w941 …/strata-huihui-ud-iq4_xs.json && docker restart strata166-407`；本轮重启 **1 次**（复测 PMC），停机 **≈4 分 20 秒**。

## 四、进度 + 队列

**175 条 / 已结 101 / 57.7%**；主线 147 / 101 / 68.7%；死块池 0/28。
队列：R90-S1 → R91-P1 → R91-P3 → R91-P4（KL 门）→ R88 → R86 → R87 → R64 → R63 → R60 → R81 → R79 → R80 → R49 → R50 → R30′

---

## 子审计复核后，又抓出两类“假回写”

第一轮我加的是**口径横幅**，但四处文档的**状态行/结论行照旧**立着——读者只会看状态行。这四处已补：

| 位置 | 状态行原文 | 现在 |
|---|---|---|
| `W919:9` | 「一条**已实证的现成损失**（PLE 表未锁定）」 | 划掉，标 `R67 = DONE_NEG`（`W920` 实测为 0） |
| `W923:9` | 「**R61 = DONE_NEG（工具不可用）**；**R60 = 关闭**」 | 划掉，写明 rocprof 只在 `HSA_TOOLS_LIB` 注入下不可用、`R60` 现为 OPEN |
| `W926:10` | 「DONE_NEG（上限仅 4.0%）」 | 补注：占比应为 **14.8–15.3%**、上限以 **3.4–4.3%** 为准，`R64` 仍 OPEN |
| `W927:93-94` | `7.5% × 73.1% = 5.5%` 整段 | 标「作废：分母与占比都是模块口径」 |

账本 R84 行里那条旧链（`53.3% ⇒ −17.9% ⇒ −3.65%`）也一并划掉，指向 `W943` 的 30.0%/−2.05%。

由此立 **纪律㉔**：撤回横幅必须带**结论动词**（“关闭不保留 / 改回 OPEN / 上限不作预期”），只改数字口径不算撤回；
另记一条验证陷阱：`\|Δ\|` 转义后 `awk -F'|'` 仍按分隔符切，**“字段数=9”不再是破表判据**，只能 `grep -c '|Δ|'`（现为 0）。

审计件 `deploy/AUDIT24_W900_W951.md` 已加 §1.1 记录这一轮；判据仍是 **P0 2 / P1 16 / P2 12 / 需复核 4**，全部整改完毕；方案表锚点 `W832@05400e73`。
