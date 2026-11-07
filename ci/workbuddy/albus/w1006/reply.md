**一、生产容器（8 字段）**

| # | 项 | 值 |
|---|---|---|
| 1 | 容器 / 镜像 | `4f387a12e84b` / `strata-gfx906:0.2.10-101`（image `5267df6dbdeb`） |
| 2 | 运行中引擎 | `eea5ea3749ad54b124330386605a18bc`，44,908,992 B（strata 0.1.56，v0.9.0） |
| 3 | config | md5 `e62685e6ff21d9e2b60c1cd622fd5a67`；exe=`/data/bin/strata-0.1.56-090`；args 37；env 9 |
| 3a | args 明细 | `--pack /data/packs/ud-q4_k_xl --native …unsloth-UD-Q4_K_XL-00001-of-00004.gguf --expert-profile … --expert-cache auto --pcie-frac 0.20 --spec 4 --spec-min-p 0.70 --mtp /data/mtp/rt --max-context 262144 --kv k8v4 --prefill auto:16384 --prompt-cache-every 8192 --expert-profile-save … --conversation-cache-mib 4096 --vision --mtp-window 8192 --vram-reserve-mib 832 --ple-io mmap --pool-workers 10` |
| 3b | env 明细 | `HSA_OVERRIDE_GFX_VERSION` `STRATA_CKPT_MOVE_PARK` `STRATA_DECODE_TIMING` `STRATA_GFX906_TUNED` `STRATA_PREFILL_CPU_SHARE` `_MAX` `STRATA_PREFILL_TIMING` `STRATA_ROCBLAS_TUNING` `STRATA_SPEC_DEPTH` |
| 4 | 健康 | `/health` ok、`loaded:true`、restarts=0、StartedAt 2026-11-05T11:58:52Z |
| 5 | 资源隔离 | `ulimit -l` = unlimited；`VmLck`: 0 kB |
| 6 | 显存布局 | expert cache 7463 slots / 21.79 GiB、borrows 2606（7.62 GiB）、882 MiB of VRAM free（启动时值，本轮未重启） |
| 7 | 回滚件 | `strata-0.1.56-080`；`cp /data/strata-huihui-ud-iq4_xs.json.bak_w976 /data/strata-huihui-ud-iq4_xs.json` + `docker restart strata166-407` |
| 8 | 本轮改动 | 生产零改动、零重启；disk = build = running = `eea5ea37…` 三方一致；本轮只读 `deploy/` 与本机账本 |

**二、主线** gfx906/mi50 @ 13254cfb · tag `mi50-0.2.10-r32-15-g13254cfb` · 落后 0 / 领先 0 · 工作树脏 0 行。
**三、本次落生产** 改动 0；重启 0 次；停机 0；代码面 0 提交（本轮只动 `deploy/` 与本机 `tools/`）。
**四、进度 + 队列** 232 条 / 已结 153 / 65.9%；死块池 0/28。队列不变：R95（外围/host 侧）→ R94 → R91 → R89 → R46 → R49 → R50。

---

## 一、范围是算出来的，不是想出来的

先在 `deploy/AUDIT_INDEX.md` 里把已审区间逐行读出（AUDIT6 W776–W785 … AUDIT24 W900–W951），再与实际存在的轮次相减，再逐个确认「这轮真的存在」：

- **W855 / W884 / W885 没有这两轮**（W854 只在 W862 的旁证里出现一句）；
- **W898 / W899 掉在缝里**：AUDIT23 覆盖到 W897，AUDIT24 从 W900 起；
- **W986–W1005 共 20 轮从未被任何审计件引用**。

合计 **22 轮**。顺带发现第一处缺陷：**`AUDIT_INDEX.md` 的覆盖表停在 AUDIT24，而 `AUDIT25_W952_W985.md` 已经在 deploy/ 里躺了一天** —— 索引本身过期，等于「哪些轮次没审」这件事不可判。

## 二、0 个 P0，3 个 P1，2 个 P2

| 号 | 级 | 轮次 | 缺陷 | 处置 |
|---|---|---|---|---|
| F1 | P1 | 元 | 索引停在 AUDIT24，AUDIT25 未登记 | 补两行 + `tools/audit_index.py` 机械校验（缺行/幽灵行都 FAIL） |
| F2 | P1 | W986–W1005 | `R95` 账本 item 仍写「1.9×」，note 仍把 dequant 3.9×／wait copy 14× 当现役证据（W1005 只改了方案） | item 按实测重写，note 补三条候选出局的实证 |
| F3 | P1 | W986–W1005 | `R88` 状态 OPEN，但假设已被自己的实测证伪（W990：timeline 与 wall 只差 **15 ms**） | 改 **DONE_NEG** + 证据 + 「工作转 R95」 |
| F4 | P2 | W1003/W1005 | `R96` 账本 OPEN，方案 新31 早已 **N/A** ⇒ 分子分母打架 | 改 **NA** |
| F5 | P2 | W1003 | 方案**两处**仍把 1.91×/1.87×/3.9×/14× 当现行事实（定义行改了、优先级表与执行序表没改） | 两处改写并划掉旧值 + `tools/plan_retired.py` 拦「退役数字以现行事实出现」 |

**两处上游数字错（外网复核，这才是「不要自己猜」的部分）**

- **#22174**：方案写「双 3090 +17%」。实测是**关掉** MMQ stream-k 后双 3090 **+9.67%**（2597→2848 t/s），单卡仅 0.073%；#22298 则是用 fastdiv + tiling **取代** stream-k。约 17% 属另一处 2×4090 的报道 ⇒ **数字与方向都错**。
- **#31188**：方案写「DGX Spark +17.2% / 5090 +5.7%」。**PR 里没有性能栏**，两处独立报道都写「无法核实 17.2%，不能归因于该 PR」⇒ 引用只能写「作者称」。

两条都不改结论（融合与 stream-k 对我们的 prefill 都不对症），但理由必须改，否则下一轮会照错的方向再做一次。

## 三、W898/W899：0 缺陷

W898（只做单流 ⇒ `R57` WITHDRAWN、`R54` 挂起、§0.2 三条重写）与 W899（`R54` DONE_NEG，并撤回「文本 sha 相同＝无差异」）在账本里状态一致、在方案里各有 3–5 处落点。唯一遗留是它们从未被任何审计件引用 —— 本件补进覆盖表。

## 四、举一反三：三处「两份东西、没人比对」

索引与审计件、W832 与本机副本、方案里同一数字的三处副本 —— 是同一种病。现在各有一道机械门：

- `tools/audit_index.py`：每个 `AUDIT<n>_*.md` 必须有行，每行必须有件。**负向 2/2**（删 AUDIT25 行、塞幽灵 AUDIT99）。
- `tools/plan_retired.py`：退役数字只能以删除线出现；出现在「事实表行」即 FAIL。**负向 5/5**（把四个旧数字塞回去、再验删除线放行）。
- `albus/w1003/mirror_check.py` 从四件扩到**六件**（+ `AUDIT_INDEX.md`、`AUDIT26`），负向 6/6。

两道新门已接进 `round_close.py` 当**硬门**（不是可选项）。六件权威件双侧逐字节：`W832 f5b8fcf0…`、`PROGRESS 788a30d9…`、`PARAM_REGISTER 0f1efc3e…`、`ID_MAP 81891d72…`、`AUDIT_INDEX 95fcc950…`、`AUDIT26 5f2f29ed…`。

产物：`deploy/AUDIT26_W898_W1005.md`、`deploy/AUDIT_INDEX.md`（补 AUDIT25/26 行 + 合计改到 W1005）、`W832`（5 处）、`PROGRESS`（+P299–P303，R88/R95/R96 三行改口径）、`tools/{audit_index,plan_retired}.py`。
