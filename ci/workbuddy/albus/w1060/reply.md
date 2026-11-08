# W1060 回执：R60 判否 + R79/R80/K8 收口 + 版本配套全面回溯终审（无未处置错版），进度 91.2%

**一、生产容器（10 字段，本轮结束时）**

| # | 字段 | 值 |
|---|---|---|
| 1 | 容器 / 镜像 | `2d765942e041` · `strata-gfx906:0.2.11-101`（image `2e7539eeb76b`）· restarts=0 |
| 2 | 运行中引擎 | `strata-0.1.57-hc4b` · md5 `0533074826258d5f96c4b65bc0ad33df`，未换件（探针 `strata-0.1.57-sumx` `35d20db7…`、`strata-0.1.57-strk` `6cece648…` **生产未装**，只在窗口臂跑过） |
| 3 | config | md5 `8d234fa38261abbee0328c80416d6835`（窗口臂独立 cfg，生产配置全程未触碰）· `exe=/data/bin/strata-0.1.57-hc4b` · args 38 / env 13，未改 |
| 3a | args 明细 | 38 项逐字未动（`--pack` `--native` `--expert-profile` `--expert-cache auto` `--pcie-frac 0.20` `--spec 4` `--spec-min-p 0.70` `--mtp` `--max-context 262144` `--kv k8v4` `--prefill auto:16384` `--prompt-cache-every 8192` `--expert-profile-save` `--conversation-cache-mib 4096` `--vision` `--mtp-window 8192` `--vram-reserve-mib 832` `--ple-io mmap` `--pool-workers 10` `--kv-grow` 等，与 W1057 同表） |
| 3b | env 明细 | 13 项逐名未动（`HSA_OVERRIDE_GFX_VERSION` `STRATA_PREFILL_CPU_SHARE` `STRATA_PREFILL_CPU_SHARE_MAX` `STRATA_ROCBLAS_TUNING` `STRATA_GFX906_TUNED` `STRATA_CKPT_MOVE_PARK` `STRATA_DECODE_TIMING` `STRATA_SPEC_DEPTH` `STRATA_PREFILL_TIMING` `STRATA_GFX906_ATTN_DP4A` `STRATA_HC_DOWN_DP4A` `STRATA_HC_DOWN_DP4A_MAX_T` `STRATA_GFX906_ATTN_LDS_PAD`） |
| 4 | 健康 | `/health` → `{"status": "ok", "max_context": 262144}` · restarts=0 · StartedAt `2026-11-08T12:08:45Z`（窗口 2 trap 还原冷启动，复测健康） |
| 5 | 资源隔离 | `ulimit -l` unlimited · `VmLck 0 kB` |
| 6 | 显存 | VRAM free 848 MiB（生产态）；expert cache 8301 槽 / 24,807 MiB；borrows：metrics 未暴露该键（本轮生产未动） |
| 7 | 回滚件 | 生产未动 ⇒ rollback 未触发；探针构建共享文件全部还原复测（gcn 双侧、overlay `quantize.cu` `9f322489`、llama-master `vecdotq.cuh` `9e0da3cb`）；工作树回 `ci/w1047-coverage` |
| 8 | 本轮改动 | 换件 0 / config 改 0 / 装机 0 / 回滚 0；**重启 2 次 / 停机 ≈1000 s**（LOGPOS 五臂窗 + 计时三臂窗，两窗 trap 还原绿）；ci/gate.py 双份加 provenance 检查（R80，代码件）；disk=build=running 三方未动 |
| 9 | ROCm（容器内） | `.info/version` **10.1.0** · HIP runtime **7.16.26323-0000000** · clang 24 · `--offload-arch=gfx906` |
| 10 | llama.cpp | **b12180 = `bcb0152876e8f0b684ba70d3defcab6cdf35adb5` + `mmq*` @ `4c1004c49221b07c3b8108977e3d1991fc9f45cc`**；**对齐实证**：上游 bcb01528 的 `vecdotq.cuh` 用 `ggml_hip_perm` == llama-master 同款（WebFetch 原文），字节级复现锚点（W1059 干净重编==hc4b）；容器 `/src/third_party` 快照=裸 builtin 版 `32877fbe…`（对照 pin 版 `quantize.cu:521` 的 d·Σq 形态） **snapshot!=build**（掉队，勿作分析源，镜像重建时同步） |

**二、主线** — `gfx906/mi50` @ e181bda5（tag `mi50-0.2.11-r33-14`）本轮未动，上游 `Niko1221/Strata` 未重算，**领先 0 / 落后 0**（从未落后），脏 0 行；**生产源基 = `03509d1b`**（Strata）+ llama-master（= pin 对齐），生产树 `pr/k10` 已对齐生产基（`4fc85a534`，引擎 drift=0）；ci 分支头本轮新增 W1060 provenance 提交（见 §4）。新证据件：`albus/w1060/`（`strk_patch.py`、`build_strk.sh`、`window_r60.sh`/`window_r60b.sh`、`run_timing.py`、`f2_client.py`、`analyze_r60.py`、`r80_gate_patch.py`、`gdnpp_gate.sh`、`land_w1060.py`）、`deploy/SOURCE_PROVENANCE.tsv`、`tools/source_provenance.py`。

**三、本次落生产** — 换件 0 / 装机 0 / **重启 2 次 / 停机 ≈1000 s** / 回滚 0。两窗口（五臂 LOGPOS + 三臂计时/F2）均独立一次性容器 + trap 还原，生产配置未改；探针构建两段式 + strings/对象断言；生产树引擎对齐提交 `4fc85a534`（只动 ci 分支的两个滞后文件至生产基，不碰生产运行态）。

**四、进度** — **546 条 / 已结 498 / 91.2%**（本轮 **+6 条 `P593`–`P598`，+4 收口**：R60 判否、R79/R80/K8 收口；R89/R46 数据推进）。队列：**R46（下一手=QSA_DUMP_STEPS 反量化相位）→ R89（QSA_DUMP cap 分布扫描）→ R95（P309）→ 治理收尾**；背包 R63/M2/X4/P309/P481；BLOCKED 池 U2/U4/G2/G4/G6（`W832 §0.1`）。

---

## 1. 版本配套全面回溯终审（机主四连问，`P597`/`P598`）

**结论：无未处置的「用错版本」情形；三类边缘情形全部当时识别并处置；机制已跟上。**

| 轴 | 应对齐 | 实证 | 判 |
|---|---|---|---|
| llama.cpp | 生产容器所用版本（pin b12180/bcb01528 + mmq@4c1004c） | 上游 bcb01528 `vecdotq.cuh:43` 用 `ggml_hip_perm` == llama-master 同款（WebFetch 原文）；W1059 字节级复现（干净重编 == hc4b md5 `05330748…`）= 全构建面版本证明 | **对齐 ✓** |
| Strata 源码 | 主线（生产基 `03509d1b`） | `pr/k10` ci 分支引擎面曾滞后 2 文件（`fused_gr.cu`/`qsa_decode_attn.cu`）→ `4fc85a534` 对齐，drift=0 | **对齐 ✓（已修）** |
| 容器 `/src` 快照 | 应 == 构建输入 | `vecdotq.cuh 32877fbe`（裸 builtin）≠ pin 版（`ggml_hip_perm`）；`mmq.cuh`/`quantize.cu` 亦异 | **snapshot!=build**（已标记；镜像重建时同步；勿作分析源） |

**用错版本专项（机主令「重新回溯」）**：① W1057–W1060 全部探针（a4probe/sumx/strk）与窗口基线均从 `03509d1b + llama-master` 构建 ⇒ 与 hc4b 同源，**A/B 单变量性成立**，窗口结论有效；② 跨树比较仅一处（W1059 sum0 vs s001b，KL 0.118）——**当时即识别树谱不同并排除出 R101 判据**（改用同树对 sum1↔sum0）；③ 静态读码错版三处（G7 行号 :3101→`:3774`、W1055 wave64 计数、worktree 读漂移文件）——已更正，且结论全部另有运行期锚定（P558/P590/ISA/复现）**无翻案**；④ 早稿一处方向记反（曾称「F10 pin 记的是容器快照」）——**以 P597 更正：F10 pin 正确，掉队的是容器快照**。

**四项报告 review（W950–W1059 全量扫描）**：F10 pin 链逐轮正确（W1031–36 记 `b11062` 为当时 pin，时点性成立；W1037 起 `b12180=bcb01528+mmq@4c1004c` 一致至今）；「领先/落后」行追踪 `gfx906/mi50` vs 上游、**从无落后** ✓；过时表述两处已更正（W1053 起「生产树 pr/k10 头 X」把 ci 分支头当生产基——现已修齐；F10 缺容器快照状态——已入清单）。

**机制跟上（防复发）**：`tools/source_provenance.py` 三查入 **round_close HARD**（①引擎漂移必须=0（allowlist 已清空）②构建输入清单 `deploy/SOURCE_PROVENANCE.tsv` 末条==生产 md5 ③容器快照≠构建必须标记）；读码纪律=`git show 03509d1b:…` 读生产基（skill 已更新）；rep 计时须逐 rep 换文本（P598 教训）。

## 2. 本轮技术结果（`P593`–`P596`）

- **R60 stream-k 判否（`P593`）**：gcn 表 Q4_K 11 行（mmq-config-gcn.cuh:120）翻 true 单变量探针 `strata-0.1.57-strk`：**R59 KL 门 FAIL**（mean 0.070006/max 3.141/top1 59/60 ≫ 0.005/99%，K-split 改算术顺序→混沌放大，P468 族）+ **速度反向**（冷跑 rep0：32K +28.1%、65K +28.2% 更慢，数据在 `albus/w1060/analyze_r60.py:1` 复算）⇒ 双证判否。K 方向切分在本形状纯亏，R60 关。
- **R79 现役行为测全（`P595`）**：致命错（STRATA_INJECT_FATAL，注入点 generate.cpp:3249）→ 当窗 503、**容器不重启**而 server 按下一请求重生引擎（R77 路径实证，P403 的「0 重启」是容器口径）；重试即恢复（49s 冷启），**prompt 缓存跨引擎重生存活**（t2 0.84s/1284tok≈98.8% 复用）、turn3 正常无需重发。
- **R80 三项 provenance（`P594`）**：ci/gate.py 加 prov/1-3 实跑抓到两个真账洞（build 路径漂移 cf2ba243≠05330748、末条 tag=- 未记账）——W937 损害类，登记流程债；hc4b retro 行已补 `prod_history.tsv`。
- **K8 GDN_PP 挂钩（`P596`）**：三用例（STRATA_GDN_PP=0/1/2）**FAILURES 0/0/0 全绿**，`gdnpp_gate.sh` 挂进 gpu-gate.yml ⇒ 每轮复测；门脚本两处自纠（^FAIL 误匹配、fail-closed rc）。
- **测量坑（`P598`）**：run_timing 首版（`albus/w1060/run_timing.py:1`） synth 文本确定性致 rep1/2 撞 prompt 缓存（真值仅 rep0 n=1）——教训入库；R60/R89 数据以此口径成立（幅度大、方向一致）。

## 3. 剩余待办（全带登记路径，队列表见 `deploy/W832_OPT_PLAN_V2.md:28`）

队列 **R46**（QSA_DUMP_STEPS 反量化相位一次重建录）→ **R89**（qsa_dump_a0.bin 5.0GB cap 分布扫描，定「只读选中 key」收益面）→ **R95**（P309 busy/phase 事件实验）→ 治理收尾；背包 R63（hoist 单测，读真源）/M2/X4/P309/P481；BLOCKED U2/U4/G2/G4/G6 各带解除条件。

## 4. CI/CD 与门

provenance 提交（`ci/w1047-coverage`）+ Downstream gate + GPU gate（push 后先同步 runner 镜像再等 run）双绿登记 `deploy/CI_RUNS.tsv`；收尾 `round_close.py` HARD 门（现含 **source_provenance** 新门）全绿后交件。
