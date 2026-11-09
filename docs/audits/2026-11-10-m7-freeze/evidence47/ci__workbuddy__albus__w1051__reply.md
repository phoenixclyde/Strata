# W1051 回执：R113 全结 + R114 G2 判否 + decode 确定性新铁律

**一、生产容器（10 字段，本轮结束时）**

| # | 字段 | 值 |
|---|---|---|
| 1 | 容器 / 镜像 | `2d765942e041` · `strata-gfx906:0.2.11-101` · restarts=0 |
| 2 | 运行中引擎 | `strata-0.1.57-hc4b` · md5 `0533074826258d5f96c4b65bc0ad33df` · 43,679,864 B，未换件 |
| 3 | config | md5 `8d234fa38261abbee0328c80416d6835`（W1049 装机态原样）· `exe=/data/bin/strata-0.1.57-hc4b` · args 38 / env 13，未改 |
| 3a | args | 38 项逐字未动：`--pack` `--native` `--expert-profile` `--expert-cache auto` `--pcie-frac 0.20` `--spec 4` `--spec-min-p 0.70` `--mtp` `--max-context 262144` `--kv k8v4` `--prefill auto:16384` `--prompt-cache-every 8192` `--expert-profile-save` `--conversation-cache-mib 4096` `--vision` `--mtp-window 8192` `--vram-reserve-mib 832` `--ple-io mmap` `--pool-workers 10` `--kv-grow` 等 |
| 3b | env | 13 项逐名未动（`HSA_OVERRIDE_GFX_VERSION` `STRATA_PREFILL_CPU_SHARE` `STRATA_PREFILL_CPU_SHARE_MAX` `STRATA_ROCBLAS_TUNING` `STRATA_GFX906_TUNED` `STRATA_CKPT_MOVE_PARK` `STRATA_DECODE_TIMING` `STRATA_SPEC_DEPTH` `STRATA_PREFILL_TIMING` `STRATA_GFX906_ATTN_DP4A=1` `STRATA_HC_DOWN_DP4A=1` `STRATA_HC_DOWN_DP4A_MAX_T=6` `STRATA_GFX906_ATTN_LDS_PAD=1`） |
| 4 | 健康 | `/health` ok · restarts=0 · StartedAt `2026-11-07T20:22:08Z`（最终对齐冷启动） |
| 5 | 资源隔离 | `ulimit -l` unlimited · `memlock=-1:-1` · `VmLck 0 kB` |
| 6 | 显存 | **VRAM free 849,211,392 B（0.79 GiB）**；expert cache 8301 槽 / 24.23 GiB；borrows 2609 槽 (7.62 GiB) |
| 7 | 回滚件 | `attn`（`3b758f88…`）+ `kvg`；备份 `tmp/w1051/cfg_*_pre.bak`；rollback = `cp` 回备份 json 并**冷重启**容器（≈45 s；见 §5 trap 教训：只 cp 不重启会让旧进程驻留） |
| 8 | 本轮改动 | **零落生产**：换件 0、config 改 0；最终 disk = build = running（md5 `05330748…` 三方一致）；**重启 11 次 / 停机 ~960 s**（四窗 + 1 次收尾对齐）/ 装机 0 / 回滚 0 |
| 9 | ROCm | 打包 .info/version 10.1.0；HIP 7.16.26323；clang 24 · `--offload-arch=gfx906` |
| 10 | llama.cpp | b12180 = `bcb0152876e8f0b684ba70d3defcab6cdf35adb5` + `mmq*` @ `4c1004c49221b07c3b8108977e3d1991fc9f45cc` |

**二、主线** — `gfx906/mi50` @ e181bda5（`mi50-0.2.11-r33-14-2-ge181bda5`）；生产树 `pr/k10`，领先 2 / 落后 0 / 脏 0 行，上游本轮未重算。候选留档：`gfx906/r114`（GDN dot2，md5 `d909d597…`）+ `gfx906/r113`（#30837 断言）。CI：`ci/w1047-coverage`（W1051 provenance run 见收工行）。

**三、本次落生产** — **零**：重启 0 次为装机、0 分钟停机为装机；四个窗口的 10 次重启/停机全部是 A/B 取证，带 trap 自还原，生产 config 与 exe 逐字节不变（md5 复核）。

**四、进度** — **502 条 / 已结 410 / 81.7%**（`tools/progress.py` 派生）。新增 `P551`–`P555`、`R115`；R113 结案、R114 结案（判否）。

队列：**R115（shared_expert swiglu 份额量化→融合候选）** → **R110/R112（k8v4 PV-dot8 真实 P/V dump）** → **R111（GPU self-hosted runner）** → **R105（gfx906 能力清单）** → **R107（audit 欠账 20 轮，机主自理）**。

## 1. R113 全结：4c1004c 后 5 提交逐个判毕（P551）

全部基于 GitHub API 真实 diff，不猜：

| 提交 | 内容 | 判 |
|---|---|---|
| `1a24df16` #30837 | `static_assert(I % warp_size==0)` 1 行 | 已验证不变量（P549，W1050） |
| `eb4e244b` #31373 | RDNA4_M（gfx1170/1171）家族 | **判否**：改动全在 RDNA4_M 宏下，GCN 路径零变化 |
| `5ce06fc7` #31296 | NVFP4 gate/up+GLU 融进 MMQ | **判否**：Blackwell NVFP4 特性；本树 `mmq_nvfp4_w4a4/w4a8` 在但模型是 Q4_K、路径未启用（R74 若启用可参考形态） |
| `69ee2ecc` #31047 | MoE tile_spec 线性化 | **判否**：`mmq.cuh` write_back 签名变更（`get_rows_to_sorted`→`ids_dst`）破坏本树 `src/prefill/moe_mmq.cu` 25 处契约；`ncols_opt` 无条件化只对 `ggml_cuda_mul_mat_q` 生效（本树不走） |
| `c49edf09` #29948 | gate/up 交错行 + GLU 融进 MMQ | **判否（已被覆盖）**：`s2_expert_grouped.cu:173` 注释明示 `silu(gate)*up` 在融合内核 epilogue（`swiglu.cuh`）、"the standalone pass it replaced is gone"，gate/up 行连续布局与 #29948 同构 |

**举一反三**（判 c49edf09 时顺藤）：routed 专家已融合，但 `shared_expert.cu:402/441/443` 仍有独立 `swiglu_kernel<<<>>>` 两形态（shared 专家 gate/up 与 GLU 未融合，逐 token 全跑，router+shared 相位 8K 271 ms）→ **R115** 立项（P555）。

## 2. R114 G2 三层门（P552/P553/P554）——判否，不装机

**（a）prefill 数值门 = 逐位通过，但暴露面为零。** 三对 pcompare（4 提示点×4 长度）KL mean/median/max 全 0.00000、top-1 100%：`hc≡g0`（r114 off 臂与生产 hc4b 逐位同——候选 off 路径未扰动）、`g0≡g1`、`hc≡g1`。派发链钉死（源码，非推测）：`fused_pre`（`src/core/layer.cpp:282`）= `g_fused_gdn && native_gdn_enabled() && native_bf16_projections && ssm_d_conv==4 && ssm_state_size==128`；生产 `--native` 伞开关置 `native_bf16=native_gdn=true`（`src/program/generate.cpp:4405`）⇒ 谓词真；但 `fused_gdn_ab` 是 **decode 单 token 逐层**路径，prefill 的 alpha/beta 在 `gdn conv+gates` 相位批式算（8K 46 ms）**不走此内核** ⇒ prefill 零变动是结构性必然。`gdn_ab_multi` 仅 `verify.cpp` 使用（生产不走）。

**（b）decode 性能门 = 未过采纳线。** 两次独立设计都落在噪声内：

| 设计 | 结果 | 门槛 |
|---|---|---|
| g2b 非配对 n=6×600tok | 52.92(cv2.46%) → 54.18(cv3.38%) = **+2.39%** | 2×CV 6.8% → 不显著 |
| g2c **配对** n=8×600tok（同 nonce 双臂） | 逐对 +4.88/−0.94/−2.37/+3.21/+3.80/−4.60/+2.06/+0.56% = **+0.82%** | 2×SE 2.17% → 不显著 |

曝光面数学自洽（不猜）：微基准 1.330× 真实（W1050），但 ab 份额 = 7.65 µs/call × 2 投影 × 36 层 ≈ 0.55 ms / 18.9 ms decode 步 ≈ **2.9%**，预期端到端 ≈ **+1%**——恰与 +0.82% 一致。**收益真实但太小，低于 2×CV 采纳线 ⇒ 不换二进制。** prefill gdn 相位佐证：1154.3 vs 1155.7 ms、`conv+gates` 六次全 46/15 ms（cv 0.00%）零变动。per-row 2^k 缩放预案**不适用**（失败因收益不可检出而非精度损失）。留档复开条件：GDN 形状变化使 ab 占比上升，或与其它微收益打包进同一次重编后统一 A/B。

**（c）decode 数值面 = fp16 噪声真实暴露，但有确定性对照背书。** g2c 同提示贪心 600-token 文本对 **8/8 在 char 38–304 早期分歧**（同义词级 argmax 翻转后自回归发散；g2b 单对 char 479 detect/identify 同类）。g2d 确定性对照钉死归因：同臂两次冷启 **T1≡T3 逐位相同**（2402 B 全等）⇒ harness 确定、翻转归因 dot2 的 fp16 舍入；跨臂 T1 vs T4 在 char 224 翻，与 g2c pair1 **同位置复现**（翻转位确定性）。若将来打包采纳，数值验收走 36 题答案门（W807/8 decode 传统），不是文本逐位。

## 3. 方法论新铁律（P554 ③，举一反三）

**g2d 的 T1≠T2**：同会话缓存重放（`cached_tokens=2092`）生成的文本与冷算路径**不同值**——缓存恢复的 KV 与重算 KV 不等价。⇒ **今后任何数值门 / A/B 文本对比，禁止使用缓存命中数据，必须逐请求冷启**（跨重启缓存存活已由 `cached_tokens=0` 反证为不存活，配对设计因此成立——这也是 g2c 配对法的合法性前提）。此律适用于一切 decode 侧数值工作。

## 4. 边界与纠错留痕

- 工程教训：① nohup 后台启动会拽住 `base64 -d | bash` 的 SSH 管道（超时假死）——用双 fork `(setsid … &)` 收敛；② 推理模型的响应正文在 `message.content`（可能为 null，reasoning 在 `reasoning_content`）——取文要两处兜底；③ 窗口脚本里 python 的 stdout 要 tee 进 log，否则被 nohup 吞掉；④ **窗口 trap 的还原必须「cp config + 冷重启」两步**——g2d 的 trap 只 cp 了 config，容器还在跑最后一个臂的 r114 进程（`docker start` 对已运行容器是 no-op），盘面/运行面分叉，被 `binary_integrity --live`（disk != running）抓出后冷重启对齐；trap/restore 类脚本今后一律把「确认进程 exe 与 config 一致」写成显式断言。
- 「不冒充完成」：R115 未动（只立项）；R110/R112、R111、R105 未动；R107 欠账 20 轮在册（机主自理）。

落点可复核：派发链 `src/core/layer.cpp:282`（fused_pre）、`src/program/generate.cpp:4405`（--native 伞）、`src/core/layer.cpp:322`（fused_gdn_ab 调用）；融合证据 `src/kernels/cuda/s2_expert_grouped.cu:173`、残余 `src/kernels/cuda/shared_expert.cu:402/441/443`；窗口件 `albus/w1051/window_g2.sh`/`window_g2b.sh`/`window_g2c.sh`/`window_g2d.sh`、解析 `albus/w1051/parse_g2.py`、数据 `albus/w1051/phase_g2.txt`/`pcompare_g2.txt`/`decode_g2c.txt`/`text_a_off.txt`/`text_b_on.txt`；判决入账 `albus/w1051/land_w1051.py`。
