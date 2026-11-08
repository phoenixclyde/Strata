# W1052 回执：队列主体推完——R105/R110/R111/R112/R115 五关 + R116 立项

**一、生产容器（10 字段，本轮结束时）**

| # | 字段 | 值 |
|---|---|---|
| 1 | 容器 / 镜像 | `2d765942e041` · `strata-gfx906:0.2.11-101` · restarts=0 |
| 2 | 运行中引擎 | `strata-0.1.57-hc4b` · md5 `0533074826258d5f96c4b65bc0ad33df` · 43,679,864 B，未换件 |
| 3 | config | md5 `8d234fa38261abbee0328c80416d6835`（W1049 装机态原样）· `exe=/data/bin/strata-0.1.57-hc4b` · args 38 / env 13，未改 |
| 3a | args 明细 | 38 项逐字未动（`--pack` `/data/packs/ud-q4_k_xl` `--native` `…UD-Q4_K_XL-00001-of-00004.gguf` `--expert-profile` `--expert-cache auto` `--pcie-frac 0.20` `--spec 4` `--spec-min-p 0.70` `--mtp` `--max-context 262144` `--kv k8v4` `--prefill auto:16384` `--prompt-cache-every 8192` `--expert-profile-save` `--conversation-cache-mib 4096` `--vision` `--mtp-window 8192` `--vram-reserve-mib 832` `--ple-io mmap` `--pool-workers 10` `--kv-grow`） |
| 3b | env 明细 | 13 项逐名未动（`HSA_OVERRIDE_GFX_VERSION` `STRATA_PREFILL_CPU_SHARE` `STRATA_PREFILL_CPU_SHARE_MAX` `STRATA_ROCBLAS_TUNING` `STRATA_GFX906_TUNED` `STRATA_CKPT_MOVE_PARK` `STRATA_DECODE_TIMING` `STRATA_SPEC_DEPTH` `STRATA_PREFILL_TIMING` `STRATA_GFX906_ATTN_DP4A=1` `STRATA_HC_DOWN_DP4A=1` `STRATA_HC_DOWN_DP4A_MAX_T=6` `STRATA_GFX906_ATTN_LDS_PAD=1`） |
| 4 | 健康 | `/health` ok · restarts=0 · StartedAt `2026-11-08T05:14:12Z`（PV 窗末次还原）· **盘=运一致**（`/proc/PID/exe` md5 == 磁盘 hc4b） |
| 5 | 资源隔离 | `ulimit -l` unlimited · `memlock=-1:-1` · `VmLck 0 kB` |
| 6 | 显存 | **VRAM free 849,211,392 B（0.79 GiB）**；expert cache 8301 槽 / 24.23 GiB；borrows 2609 槽 (7.62 GiB) |
| 7 | 回滚件 | `attn`（`3b758f88…`）+ `kvg`；备份 `tmp/w1052/cfg_pv_pre.bak`；rollback = `cp` 回备份 json 并**冷重启**（≈45 s） |
| 8 | 本轮改动 | **零落生产**：换件 0、config 改 0；disk = build = running **三方一致**；**重启 8 次 / 停机 480 s**（3 个 PV 取数窗，各带 trap 冷还原）/ 装机 0 / **装机停机 0 分钟** / 回滚 0 |
| 9 | ROCm | 打包 .info/version 10.1.0；HIP 7.16.26323；clang 24 · `--offload-arch=gfx906` |
| 10 | llama.cpp | b12180 = `bcb0152876e8f0b684ba70d3defcab6cdf35adb5` + `mmq*` @ `4c1004c49221b07c3b8108977e3d1991fc9f45cc` |

**二、主线** — `gfx906/mi50` @ e181bda5（`mi50-0.2.11-r33-14-2-ge181bda5`）；生产树 `pr/k10`，领先 2 / 落后 0 / 脏 0 行，上游本轮未重算。新证据件：探针 `gfx906/pvprobe@d0ea57396`（`strata-0.1.57-pvprobe`，未装）；CI 新 workflow `gpu-gate.yml @ 702c6efbf`，GPU run **42450933745 success**（runner `strata166-gfx906`）；runner 镜像 `/home/ghrunner/mirror/Strata.git` @ `702c6efbf`。

**三、本次落生产** — **零**：装机 0 / **0 分钟停机**（为装机）；窗口取证累计 **重启 8 次 / 停机 480 s**（3 个 PV 取数窗，trap 冷还原）。新增常驻件一项（runner systemd 服务，166 主机侧，不动生产容器）；生产 disk = build = running 三方一致（md5 `05330748…`）。

**四、进度** — **508 条 / 已结 419 / 82.5%**。队列：**R116（PV dot4 离线预算）** → **R107（audit 21 轮，你自理）**。R105/R110/R111/R112/R113/R114/R115 全部判毕——**队列主体推完**。

## 1. R115 更正判否（P556）：独立 swiglu 不在生产路径

追谓词三跳：`fused_swiglu_q81_enabled()` **默认 ON**（`shared_expert.cu:207`，env 缺省即开）× `native_down` 生产真（down_type Q5_1/Q8_0 ⊂ `native_mmvq.cu:3575` 支持名单）⇒ 单 token 与批量两路都走 **`native_swiglu_quantize_q8_1` 融合变体**；独立 swiglu 仅在 fallback 分支。W1051 的「残余」是没跟到谓词——本轮更正（P555 纠错入账）。gemm+swiglu 一体化残余估 <0.3%，记 REF 不立项（P560）。

## 2. R110/R112 判否（P557）：真实 P/V dump 误差预算 FAIL

- **探针**（零停机原型，生产不装）：`attn_chunk_body`（`qsa_decode_attn.cu:125`）softmax 后 PV 前 env 门控捕获 **kernel-local `sp[h][c]`**（dot8 方案要量化的就是它）+ 原始 Q4_0 V 块 + srow → `strata-0.1.57-pvprobe`（md5 `df8813f7…`）。
- **真实分布**（22 记录 / **12,804 P 值** / 67,584 输出）：P 长尾实锤——min 3.6e-7、中位 8.0e-3、90 分位 0.166、**峰值恒 1.0**（chunk-local exp(a−m)）。
- **误差预算**（R110 规格：P·Vscale 按 8-cell 组量化 int4、V nibble−8、int32 按组即转 fp32）：**rel-rms 4.595%**、max_abs 0.83（最差点 ref −10.26→−9.43）。合成上界 6.23% 只略悲观——**真实分布无红利**。对照项目数值线（KV8 采纳 = logits KL 0.0139；内核换代 1e-4 级）：**无预算 ⇒ PV-dot8 不接 OPT，判否**。
- **死因钉死**：int4 按组 scale=max/7 时，P 长尾（中位 0.008×max）直接量化成 0。**举一反三 → R116**：P int8（128 级，误差 ~16× 小）× V nibble→int8 **无损**（Q4_0 的 V 本来就是 int4，符号扩展进 int8 不丢），走 `v_dot4_i32_i8`；代价 V 读流量 ×2。用 `albus/w1052/pv.dump` 的 22 记录离线重放即可先算误差预算，零停机（离线分析脚本 `albus/w1052/pv_budget.py:1`）。

## 3. R111 上线（P558）：GPU runner + gpu-gate 端到端

- **runner**：v2.338.2（官方 sha256 `baebf204…7c40` 校验；GitHub 直连 25KB/s → **gh-proxy.com 29.5MB/s**，12 秒 228MB）装于 166，`ghrunner` 专用用户（render 组进 GPU、sudoers.d **仅放行 docker**），systemd 常驻，API 实证 `online`，labels `self-hosted,linux,x64,gfx906`。
- **安全边界（本仓 PUBLIC，上网核实通用建议后自定义）**：公开仓挂 runner 的通用禁令核心是"PR 可任意执行代码"——本仓 workflow **无 `pull_request`/`pull_request_target` 触发** ⇒ 该向量封死，残余风险=有写权限账号被攻破（登记备查）；label 隔离（`runs-on: [self-hosted, gfx906]`，禁裸 `self-hosted`）+ 工作流内注释立规。可选加固（转 private / ephemeral）已记档。
- **端到端**：`gpu-gate.yml @ 702c6efbf`（device/rocminfo/ci 语法冒烟）run **42450933745 success 落本 runner**。工程化补丁：runner 的 CN→GitHub 慢网会让 checkout 爬行 → **本地 bare 镜像 + `git config insteadOf`**（`/home/ghrunner/mirror/Strata.git`）拆掉瓶颈，checkout 从小时级到秒级。

## 4. R105 收口（P559）：93 处五类总账

全树枚举 93 处 `STRATA_HIP_GFX906`，三问分类入 `albus/w1039/GFX906_GATES.md §5`：**A 正向门 60**（为 gfx906 写的优化，维护过）/ **B 硬件事实 3**（permlanex16、wave32 族、pre75/DPP——均无生产损失）/ **C 撰写假设·可选开关被编译掉 8**（5 已点名：3 组可零风险解开见 §2、expert_cache 恒 discrete 自证、prompt_attn 不可达）/ **D API·平台分工 16** / **E 构建开关·无关 6**。⇒「gfx906 少掉的能力」清单 = B3 + C5，B 类不损失功能。

## 5. 边界与纠错留痕

- R107 审计欠账 21 轮在册（你自理，只记账）。
- 工程教训：① shell replace 静默落空（尾分号差异）要 assert 计数；② 探针的 dump 路径必须在服务容器挂载面内（/data）；③ 下载走镜像也要**sha256 对官方 digest**；④ git clone --mirror 跨用户要 root 克隆后移交属主。
- 落点可复核：判据行 `deploy/PROGRESS.tsv`（P556–P560）；探针件 `albus/w1052/pv_dump_patch.py`/`build_pvprobe.sh`/`pv_budget.py`/`pv.dump`；runner 件 `albus/w1052/gpu-gate.yml`/`runner_install3.log`；93 处账 `albus/w1039/GFX906_GATES.md §5`；方案回写 `deploy/W832_OPT_PLAN_V2.md` W1052 段。
