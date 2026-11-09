# W1059 回执：待办大清扫——本轮 +38 收口（P392 KL=0 / R101 定案 / R91·R86·R64·R81 等判否），进度 90.4%

**一、生产容器（10 字段，本轮结束时）**

| # | 字段 | 值 |
|---|---|---|
| 1 | 容器 / 镜像 | `2d765942e041` · `strata-gfx906:0.2.11-101`（image `2e7539eeb76b`）· restarts=0 |
| 2 | 运行中引擎 | `strata-0.1.57-hc4b` · md5 `0533074826258d5f96c4b65bc0ad33df`，未换件（sumx 探针 `strata-0.1.57-sumx` md5 `35d20db7ab8cd5b92ab5c65f2e7e1324` **生产未装**，只在窗口臂里跑过） |
| 3 | config | md5 `8d234fa38261abbee0328c80416d6835`（窗口臂用独立 `/data/w1059/cfg_*.json`，**生产配置全程未触碰**）· `exe=/data/bin/strata-0.1.57-hc4b` · args 38 / env 13，未改 |
| 3a | args 明细 | 38 项逐字未动（`--pack` `--native` `--expert-profile` `--expert-cache auto` `--pcie-frac 0.20` `--spec 4` `--spec-min-p 0.70` `--mtp` `--max-context 262144` `--kv k8v4` `--prefill auto:16384` `--prompt-cache-every 8192` `--expert-profile-save` `--conversation-cache-mib 4096` `--vision` `--mtp-window 8192` `--vram-reserve-mib 832` `--ple-io mmap` `--pool-workers 10` `--kv-grow` 等，与 W1057 同表） |
| 3b | env 明细 | 13 项逐名未动（`HSA_OVERRIDE_GFX_VERSION` `STRATA_PREFILL_CPU_SHARE` `STRATA_PREFILL_CPU_SHARE_MAX` `STRATA_ROCBLAS_TUNING` `STRATA_GFX906_TUNED` `STRATA_CKPT_MOVE_PARK` `STRATA_DECODE_TIMING` `STRATA_SPEC_DEPTH` `STRATA_PREFILL_TIMING` `STRATA_GFX906_ATTN_DP4A` `STRATA_HC_DOWN_DP4A` `STRATA_HC_DOWN_DP4A_MAX_T` `STRATA_GFX906_ATTN_LDS_PAD`） |
| 4 | 健康 | `/health` → `{"status": "ok", "max_context": 262144}` · restarts=0 · StartedAt `2026-11-08T11:16:46Z`（LOGPOS 窗口 trap 还原的冷启动，复测健康） |
| 5 | 资源隔离 | `ulimit -l` unlimited · `VmLck 0 kB` |
| 6 | 显存 | VRAM used 31.65 GiB（生产态，与窗口前一致）；expert cache 8301 槽 / 24,807 MiB；borrows：metrics 未暴露该键（本轮生产未动） |
| 7 | 回滚件 | 生产未动 ⇒ rollback 未触发；sumx 探针构建的共享文件（overlay `quantize.cu`）**已还原 md5 `9f322489` 复测一致**（`albus/w1059/build_sumx.sh:20` 两段式构建 + 还原断言）；工作树回 `ci/w1047-coverage` |
| 8 | 本轮改动 | 换件 0 / config 改 0 / 装机 0 / 回滚 0；**重启 1 次 / 停机 ≈500 s**（五臂 LOGPOS 窗口 19:08–19:17，1 停 1 启 + trap 还原绿）；disk=build=running 三方未动 |
| 9 | ROCm（容器内） | `.info/version` **10.1.0** · HIP runtime **7.16.26323-0000000** · clang 24 · `--offload-arch=gfx906` |
| 10 | llama.cpp | **b12180 = `bcb0152876e8f0b684ba70d3defcab6cdf35adb5`** + `mmq*` @ `4c1004c49221b07c3b8108977e3d1991fc9f45cc`（镜像未换 ⇒ pin 未变） |

**二、主线** — `gfx906/mi50` @ e181bda5 本轮未动，上游未重算，**领先 0 / 落后 0**，脏 0 行；生产树 `pr/k10` 头 **`f290612dd`**（W1058 提交）→ 本轮新增 W1059 provenance 提交（见 §5）。新证据件：`albus/w1059/`（`sumx_patch.py`、`build_sumx.sh`、`window_logpos.sh`、`kl_cmp.py`、`land_census.py`/`land_census2.py`/`land_window.py`/`land_final.py`、`data/w1059/logpos_*.tsv` 五臂）。

**三、本次落生产** — 换件 0 / 装机 0 / **重启 1 次 / 停机 ≈500 s** / 回滚 0。LOGPOS 五臂窗口（独立一次性容器 + trap 还原），生产配置全程未改；sumx 探针构建两段式（configure 收敛后打补丁），overlay 还原复测。

**四、进度** — **540 条 / 已结 488 / 90.4%**（本轮 **+38 收口**：P392·P590–P592 新证 + R91·R84·R101·R64·R81·R86 族·R19·R39·R42·R45·R49·R50·R72·R94·G1·G3·G5·G7–G10·P1c·P266·P335·P424·P455·P481·D28·X3·X5·X6·X7 等）。队列：**R46（attention 效率，上限 3.3×）> R60（stream-k，R59 门已过）→ R89（depth A/B）→ R95（P309）→ 治理 R80/R79 → R85 验收随行**；BLOCKED 池（U2/U4/G2/G4/G6）与背包（R63/M2/K8/X4/P309/P481）按登记路径推进（`W832 §0.1`）。

---

## 1. 本轮主结果：P392 数值门 KL=0 + R101 定案（`P590`/`P591`）

五臂 LOGPOS 窗口（W824 §10 协议：`STRATA_LOGPOS` + `TOPK=64` + `CPU_SHARE=0`，kl_prop 口径 60 位置/臂，`albus/w1059/kl_cmp.py:34`）：

| 对 | 含义 | KL mean | KL max | top1 | 判 |
|---|---|---|---|---|---|
| s010 vs s001b | **K10 整栈 vs 基线** | **0.000000** | **0.000000** | 60/60 | **逐字节同 md5 ⇒ 数值逐位等价** |
| sum1 vs sum0 | **Σx ↔ d·Σq（单变量）** | **0.104091** | **4.372991** | 58/60 | 差异非平凡 |
| s001a vs s001b | 首臂 profile 态效应 | 0.004404 | 0.160985 | 60/60 | 协议污染源（非内核噪声） |

- **P392 闭案（KL=0）**：K10 栈（#29953 越界读修复 + #30168/#30553）与基线**逐位等价**（TSV md5 同）——P407 的「源码级等价（同一 `launch_mul_mat_q` 实例）」获**运行期实证**；配合 P390 速度免费（534.83/716.72 vs 532.76/714.89）⇒ **整栈可零代价拿**。#29953 的数值判定（P392 欠账）= 0 差异。
- **R101 定案**：上游 `8fc0376`（#31247「cuda: potential fix for Q8_1 correction sum」，1 文件 16+/14−，已上网核实）的语义（Σx→d·Σq）**已在本树**（`quantize.cu:521 sum = d * float(sum_q)`）⇒ cherry-pick 是空操作。单变量实测（`strata-0.1.57-sumx`，`STRATA_SUMX` env 门控把 DS4/D2S6 块和退回 Σx 裸和，`albus/w1059/sumx_patch.py:24`）证明该差异**非平凡**（KL 0.104）：修正项的输入和在近零和块上被放大 ⇒ #31247 的一致性修正在正确侧，本树已在正确侧。旧判据（48-token 贪心指纹）已被 P388 废，本条以 LOGPOS 单变量收口。
- **协议缺陷登记（`P592`）**：首臂 `--expert-profile-save` 生成态使 KL 0.0044/max 0.161（top1 全同）——数值窗口地板对必须用 profile 就位后的臂，或先空跑一臂暖 profile；本轮地板对按污染解读，跨容器确定性另有实证（s001b vs s010 不同二进制逐字节同）。

## 2. 大清扫：38 项收口的判定要点（`P585`–`P592` + land_census 族）

- **R91 dot8 判否于 ROI（`P587`/P589 收口）**：P0–P4 精度链全过门（W1058），但收益上界 <2×CV 3.2%（W921 计算阶段判死）——指令口径 W943 census −2.05%（理想）、布局口径 LDS 读 10.6% kernel 指令减半 ⇒ **≤−0.7% e2e**（×VALUBusy 67% 转化）、纯密度实测 0.962×（P587 B 臂）。**修正**：MemUnitStalled/LDS 流量计数我方从未采集（CSV 只有 VALUBusy；前稿误把 hipfire 外证当自家数）；如需更强证据可补 4 min rocprof。R84 随 R91 并案收口。
- **前置门判否族**：R64（32K attn **15.3–19.0%** < 25% 门，W1035 318 点源；长度指数 1.20 ⇒ 占比平坦）；R86 族 ×4（down-only 上限 −2.6~−3.3% < 5% 立项门，W1005）；R39（四轴全测，全因子 <2×CV）；R94（三版基线 KL 0.0733–0.0770 ≫ 门 0.0139，判据不可能过，P539）。
- **实跑判死族**（P428/P558/P259x 等既有臂）：G8（bank 冲突 0 命中）/ G9（hazard 计数 0）/ G7（wave64 无实测收益）/ G5（R95 族全出局）/ G3（P343 重构级）/ G10（P553–P555 全关）/ G1（热路径外）/ R50（W945/W948 两路）/ R19（54 µs/tok 上限 1.2%）/ X3（R41/R40）/ P266+P335（ptrace 双堵，改 launcher 通道）/ P424（s_waitcnt −0.44%）/ P455（救靶不存在）/ D28+P1c（§6.6 判读 + P259x）。
- **存量清零**：R42（move-only 已在产）、R45（RING_RESERVE 已删）、R49（P427 手法已拿）、R72（R104 超越目标）、X5/X6/X7（闲置/已覆盖）。
- **首臂/构树两坑入库**：①CMake configure 时**重写 overlay**（`cmake/strata_ggml_tq_overlay.cmake`）——checkout 触发 reconfigure 会静默洗掉补丁 ⇒ 构建必须两段式（先 ninja 收敛再打补丁）+ 字符串断言进二进制（`build_sumx.sh:20`）；②nvfp4/mxfp4 共享 launch 形态，补丁替换必须按内核名锚定（W1057 a4sim 注释早有此警告）。

## 3. 剩余 25 项的推进路径（全部已登记）

- **队列主线**：R46（下一手=STRATA_QSA_DUMP 一次重建录，反量化细分割）> R60（stream-k：gcn 表 11 行翻 true + 重链 + 32K/64K 各 3 rep + R59 KL 门，R59 前置已过）→ R89（depth 1×/3×/6× 绝对 ms，3 次 TIMING 同 ids）→ R95（P309 busy/phase 事件实验）→ 治理 R80（ci/gate.py 三查并 HARD）/ R79（现役行为判读 + #3747 搭车）。
- **背包**（按需捞）：R63 hoist 单测 / M2（钳 PLE 路线 J5）/ K8（cron 挂 task）/ X4（随 v0.9.0）/ P481（搭车 R117）/ P309（设计已定）。
- **BLOCKED 池**：U2（<8% 门）/ U4（机主批准制）/ G2·G6（R117 搭车）/ G4（随 R89）。
- **R85** = 端到端验收口径（801→≥850）随 R46/R60 兑现行。

## 4. CI/CD 与门

provenance 提交（`ci/w1047-coverage`，本轮证据件 + 账本 + 方案回写）+ Downstream gate + GPU gate（push 后先同步 runner 镜像再等 run，W1056 流程）双绿后登记 `deploy/CI_RUNS.tsv`。收尾 `round_close.py` HARD 门全绿后交件。（run id 见文末补记。）
