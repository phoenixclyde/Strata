# W1054 回执：AUDIT30 整改所有审计输出 + 方案表格清零（46→35→0）

**一、生产容器（10 字段，本轮结束时）**

| # | 字段 | 值 |
|---|---|---|
| 1 | 容器 / 镜像 | `2d765942e041` · `strata-gfx906:0.2.11-101` · restarts=0 |
| 2 | 运行中引擎 | `strata-0.1.57-hc4b` · md5 `0533074826258d5f96c4b65bc0ad33df`，未换件 |
| 3 | config | md5 `8d234fa38261abbee0328c80416d6835`（W1049 装机态原样）· `exe=/data/bin/strata-0.1.57-hc4b` · args 38 / env 13，未改 |
| 3a | args 明细 | 38 项逐字未动（`--pack` `--native` `--expert-profile` `--expert-cache auto` `--pcie-frac 0.20` `--spec 4` `--spec-min-p 0.70` `--mtp` `--max-context 262144` `--kv k8v4` `--prefill auto:16384` `--prompt-cache-every 8192` `--expert-profile-save` `--conversation-cache-mib 4096` `--vision` `--mtp-window 8192` `--vram-reserve-mib 832` `--ple-io mmap` `--pool-workers 10` `--kv-grow`） |
| 3b | env 明细 | 13 项逐名未动（`HSA_OVERRIDE_GFX_VERSION` `STRATA_PREFILL_CPU_SHARE` `STRATA_PREFILL_CPU_SHARE_MAX` `STRATA_ROCBLAS_TUNING` `STRATA_GFX906_TUNED` `STRATA_CKPT_MOVE_PARK` `STRATA_DECODE_TIMING` `STRATA_SPEC_DEPTH` `STRATA_PREFILL_TIMING` `STRATA_GFX906_ATTN_DP4A=1` `STRATA_HC_DOWN_DP4A=1` `STRATA_HC_DOWN_DP4A_MAX_T=6` `STRATA_GFX906_ATTN_LDS_PAD=1`） |
| 4 | 健康 | `/health` → `{"status": "ok", "max_context": 262144}` · restarts=0 · StartedAt `2026-11-08T05:14:12Z` |
| 5 | 资源隔离 | `ulimit -l` unlimited · `memlock=-1:-1` · `VmLck 0 kB` |
| 6 | 显存 | VRAM free 849,211,392 B（0.79 GiB）；expert cache 8301 槽 / 24.23 GiB；borrows 2609 槽 (7.62 GiB)（本轮只读） |
| 7 | 回滚件 | `attn`（`3b758f88…`）+ `kvg`；备份 `tmp/w1052/cfg_pv_pre.bak`；rollback = `cp` 回备份 json 并冷重启（≈45 s） |
| 8 | 本轮改动 | **零落生产**：换件 0、config 改 0、**重启 0 次 / 停机 0 s**、装机 0、回滚 0；disk = build = running 三方一致 |
| 9 | ROCm | 打包 .info/version 10.1.0；HIP 7.16.26323；clang 24 · `--offload-arch=gfx906` |
| 10 | llama.cpp | b12180 = `bcb0152876e8f0b684ba70d3defcab6cdf35adb5` + `mmq*` @ `4c1004c49221b07c3b8108977e3d1991fc9f45cc` |

**二、主线** — `gfx906/mi50` @ e181bda5（`mi50-0.2.11-r33-14-2-ge181bda5`）；生产树 `pr/k10`，领先 0 / 落后 0 / 脏 0 行，上游本轮未重算。审计件 `deploy/AUDIT30_OUTPUT_REMEDIATION.md`（P0=0/P1=1/P2=4）；门升级 `tools/audit_outputs.py:66`（.tsv 入点名）+ `:128`（顶层 `.bak` 禁令）；表格基线清零 `deploy/TABLE_SHAPE_BASELINE.tsv:1`；索引行 `deploy/AUDIT_INDEX.md:38`。

**三、本次落生产** — **零**：装机 0 / **0 分钟停机**；**重启 0 次 / 停机 0 s**（全部为本机文件/工具改动与 GitHub API 取证）；回滚 0。

**四、进度** — **525 条 / 已结 436 / 83.0%**（+5 条 `P573`–`P577`）。队列：**R116 → R74 → R91 → R85**（手段序 R46 > R64 > R60）→ R89 → R95 → R86 → R101（详见 `W832 §0.1`）。

## 1. AUDIT30：审计输出全整改（P573）

对象=**审计件自身**：24 件编号审计 + 42 件 COMPANIONS + 2 本台账 + 方案本体。结论 P0=0 / **P1=1** / P2=4，五条全部整改完毕。逐件体检：VERDICT 机读行 24/24 与索引 P 列相等；COMPANIONS 42/42 文件在；台账 id 唯一；撤回声明扫描 0 现行违规（AUDIT26 #31188 撤回链完整）。

## 2. P1（P574）：点名门只扫 `*.md`——304 份备份从所有门下逃逸

- **两个洞**：① `audit_ish()`（`tools/audit_outputs.py:66`）只收 `*.md` ⇒ **3 份 AUDIT24 TSV 分片**（GP4/W905-W917/GP3）从未被点名机制覆盖；② deploy/ 顶层躺着 **304 份 `.bak` 编辑副本**（PROGRESS 99、方案 53、W750/713/776 计划 64、AUDIT 件 30、SESSION_STATE 7…）——AUDIT29 A29-7 只清了 `albus/` 的 32 份报告副本，deploy/ 这层没人看过。
- **修**：`audit_ish()` 收 `.tsv`（两本台账显式豁免）+ 新 **check 5**（deploy/ 顶层禁止 `.bak`，必须进 `deploy/_bak/`）；COMPANIONS 补点名 3 份；**304 份全部收纳**（历史保留、不删）。现 `strays=0 / companions=42 / PASS`。
- **为什么是 P1 不是 P2**：备份与活件同级 = 任何按文件名/mtime 取「审计结论」的人都可能拿到过时件——W1006（索引停在 AUDIT24）的文件系统版；且洞本身在门里。

## 3. P2（P575）：方案 35 行损坏表格全修——`tables clean`（46→35→0）

- **3 处粘连行**拆分：R32‖R33、R35‖R36、R42‖R20（`||` 把两行挤成一行）；
- **~15 行短行**补齐尾格（用 `—`，如实标注「该格在历史编辑中丢失」——不编造内容）；
- **3 处内容裸竖线**转义（`max‖Δlogit‖`×2、`‖Δ‖ ≥ 2×CV`）+ 3 处多余尾格清理 + W1041 目录行补回丢失的「轮次」列；
- AUDIT27 行内 `TESTING|ADOPTED` 裸竖线同修（`deploy/AUDIT27_W1006_W1031.md:23`）；`TABLE_SHAPE_BASELINE.tsv` **清零**——今后任何新破坏立即 FAIL。
- AUDIT29 §6 两条「留待下次」边界改标 **【AUDIT30 已完成】**（P577）。

## 4. 外证（P576）：6 个上游 PR 逐条 GitHub API 复核

| PR | 标题（API 实取） | 与审计件记载 |
|---|---|---|
| #29953 | CUDA: fix MMQ out-of-bounds reads | ✓ merged |
| #30168 | CUDA: pass src1 precision to host MMQ config helpers | ✓ merged |
| #30553 | cuda: cap MMQ Stream-K blocks at available work | ✓ merged |
| #30837 | ggm-cuda: enforce DP4A MMQ tile height multiple of warp size | ✓ merged |
| #31188 | CUDA: fuse MoE gate/up matmuls and GLU in MMQ | ✓ merged（AUDIT26 误判已撤回，与现状自洽） |
| #31247 | cuda: potential fix for Q8_1 correction sum | ✓ merged |

## 5. 边界与纠错留痕

- `_bak/` 里 304 份是冻结历史证据，只收纳不清理——删否由你定。
- 短行补的 `—` 格=「内容丢失未考证」，不是真值；要真值须回对应轮次产物。
- **门自证有效一次**：AUDIT30 的 VERDICT 行初版漏了 `P3=0`，被 `audit_outputs` 当场拦下（got 0 → FAIL）——修门之后门抓的第一条就是自己的交付件。
- 落点可复核：审计件 `deploy/AUDIT30_OUTPUT_REMEDIATION.md:1`；门 `tools/audit_outputs.py:56`（`audit_ish`）、`:75`（stray_baks）；基线 `deploy/TABLE_SHAPE_BASELINE.tsv:1`；收纳区 `deploy/_bak/`（304 件）；账本行 `deploy/PROGRESS.tsv`（`P573`–`P577`）；方案回写 `deploy/W832_OPT_PLAN_V2.md` W1054 段。
