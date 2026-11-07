# W1049 四件套 — R103 移植面全收口（B2 闭案 / A2 采纳 / A1·A3·A4·A5 判否）

**一、生产容器（10 字段，2026-11-08 00:5x 只读）**

| # | 字段 | 值 |
|---|---|---|
| 1 | 容器 / 镜像 | `2d765942e041` · `strata-gfx906:0.2.11-101` · restarts=0 |
| 2 | 运行中引擎 | `strata-0.1.57-hc4b` · md5 `0533074826258d5f96c4b65bc0ad33df` · 43,679,864 B，未换件 |
| 3 | config | md5 **`8d234fa38261abbee0328c80416d6835`**（装机后；前值 `9e2df560…`）· `exe=/data/bin/strata-0.1.57-hc4b` · args 38 / env **13**（+`STRATA_GFX906_ATTN_LDS_PAD=1`） |
| 3a | args 明细 | `--serve` `--pack` `--native` `--expert-profile` `--expert-cache auto` `--pcie-frac 0.20` `--spec 4` `--spec-min-p 0.70` `--mtp` `--max-context 262144` `--kv k8v4` `--prefill auto:16384` `--prompt-cache-every 8192` `--expert-profile-save` `--conversation-cache-mib 4096` `--vision` `--mtp-window 8192` `--vram-reserve-mib 832` `--ple-io mmap` `--pool-workers 10` `--kv-grow` |
| 3b | env 明细 | `HSA_OVERRIDE_GFX_VERSION` `STRATA_PREFILL_CPU_SHARE(_MAX)` `STRATA_ROCBLAS_TUNING` `STRATA_GFX906_TUNED` `STRATA_CKPT_MOVE_PARK` `STRATA_DECODE_TIMING` `STRATA_SPEC_DEPTH` `STRATA_PREFILL_TIMING` `STRATA_GFX906_ATTN_DP4A=1` `STRATA_HC_DOWN_DP4A=1` `STRATA_HC_DOWN_DP4A_MAX_T=6` 未动；新增 `STRATA_GFX906_ATTN_LDS_PAD=1`（P536） |
| 4 | 健康 | `/health` ok · restarts=0 · StartedAt `2026-11-07T17:01:45Z` · 冷启动 43 s · 容器进程 env 实证 `ATTN_LDS_PAD=1`+`ATTN_DP4A=1` |
| 5 | 资源隔离 | `ulimit -l` unlimited · `memlock=-1:-1` · `VmLck 0 kB` |
| 6 | 显存 | **VRAM free 849,211,392 B（0.79 GiB）**；expert cache 8301 槽 / 24.23 GiB；borrows 2609 槽 (7.62 GiB) |
| 7 | 回滚件 | `attn`（`3b758f88…`）+ `kvg`；config 备份 `tmp/w1049/cfg_original.json`；rollback = 恢复 config 并重启容器 |
| 8 | 本轮改动 | 换件 0、config 改 1 次（+1 env）；disk = build = running 三方一致；**重启 26 次 / 停机 2100 s**（三窗：主窗、r103b、r103c/d）+ 装机 1 次；回滚 0 |
| 9 | ROCm 版本 | 10.1.0；HIP 7.16.26323；clang 24 · `--offload-arch=gfx906` |
| 10 | llama.cpp 版本 | b12180 = `bcb0152876e8f0b684ba70d3defcab6cdf35adb5` + `mmq*` @ `4c1004c49221b07c3b8108977e3d1991fc9f45cc` |

**二、主线** — `gfx906/mi50` @ e181bda5（`mi50-0.2.11-r33-14-2-ge181bda5`）；生产树 `pr/k10`，领先 2 / 落后 0 / 脏 0 行，上游本轮未重算。本轮新增候选分支 `gfx906/r103x@4a78f50ce`（A1+A5+诊断位开关包）、`gfx906/r103ilp`（A4 flag 构建）；`ci/retro/*` 10 条与 `ci/w1047-coverage@46f579a10` 在册。

**三、本次落生产** — **config +1 env：`STRATA_GFX906_ATTN_LDS_PAD=1`（P536，A2）**，二进制不换。D1–D7 全 PASS 后执行：config `9e2df560→8d234fa3`、冷启动 43 s、`/proc/environ` 双开关在证、restarts=0。备份 `tmp/w1049/cfg_preinstall_w1049.bak`，rollback=还原 config 并重启。本轮窗口累计 **重启 26 次 / 停机 2100 s**。

**四、进度** — **493 条 / 已结 399 / 80.9%**。R103/R109 全收口；新增 P536–P542（七项判决）、R114（B4 转正）。

队列：**R114（GDN fp16 dot2，先 bf16→fp16 KL 门）** → **R113（mmq 二段：#30837 首选）** → **R110/R112（k8v4 PV-dot8 真实 P/V）** → **R111（GPU runner）** → **R106（gen_config 对齐）** → **R105（gfx906 能力清单）** → **R107（audit 17 轮欠账）**。

## 1. R103 移植面收口表（每项已装或已判，无悬空）

| 项 | 判 | 证据（W1049 三窗，n=3 破缓存） |
|---|---|---|
| **B2** | **DONE via B1（闭案）** | 派发四层全查：① gated 编译排除 ② `prompt_attn_batch` `return false`（`qsa_prompt_attn.cu` STRATA_HIP_GFX906）③ `STRATA_PATTN_BUILT=0` ④ `qsa_decode_attn_batch` 循环=真热路径。B2 与 B1 同模板 `OPT&2`（`qsa_decode_attn.cu:234/306`）；收益兑现 −11.3%（1261.7→1119.0 复证 P499） |
| **B3** | DONE（W1047 装机） | HC down DP4A + MAX_T=6（P527/P528） |
| **A2** | **采纳（P536）** | G1 双重 bitwise（f≡c、**e≡m** KL 0.00000）；8K qsa attn 组合 **1103.7 vs 1119.0（−1.37%）**、地板 1261.7（−12.5%）；2.5K 226 vs 230；decode 49.2 vs 50.3 持平 |
| A1 | 判否（P537） | bitwise✓（f≡g KL 0）；router+shared 271 vs 271 ms、decode 47 vs 49——不可检出 |
| A5 | 判否（P538） | bitwise✓（f≡h KL 0）；gather 24-25 ms、占 0.3%——不可检出 |
| A3 | 判否（P539） | qsa attn 1255 vs 1261.7（−0.56% 显著）但整条 GPU +0.45% 不显著 |
| A4 | 判否（P540） | a≡k KL 0（调度 bitwise）但 qsa attn 1762（**+39.6%**）、整条 +6.2%——有害；社区 +10~20% 属 GEMM TU |
| 诊断位 | P457 结案（P541） | REDUCE12 单独 KL=0 ⇒ 归约无辜；CTLREAD KL **0.0948**/top-1 75% ⇒「手工 K 读+晚 scale 无辜」**证伪**；F16Q KL 0.034 |

## 2. 方法与纠错

- **计时三窗**：主窗（8 计时臂+8 logits dump+7 pcompare）→ r103b（prompt-cache 破除后 n=3 重测，发现首窗 2.5K 被缓存吞掉）→ r103c/d（组合臂 DP4A+PAD + e/m G1）。每臂单开关、同地板（R109 纪律）。
- **pcompare 七对**：a≡f、f≡g、f≡h、a≡d 均 KL 0.00000；f vs i 0.0948；f vs j 0.0340；a≡k 0.00000；补 f≡c、e≡m 0.00000。
- **构建纠错**：r103ilp 首跑 build.ninja（root 属主）patch 静默失败 ⇒ 二进制 md5 与 hc4b 撞车——「同 md5=没生效」当场抓住；docker root 重打后 md5 `c8b47b16…` 才真不同。
- **A4 与外证冲突不和稀泥**：社区「max-ilp +10~20% prefill」是全局 flag；我们逐 TU 实测 attn +39.6%。两者都记：收益在别的 TU（GEMM），抄全局会伤 attn。
- **落点与门可复核**：派发 `src/prefill/prefill.cpp`（①②③④）；OPT 位 `src/kernels/cuda/qsa_decode_attn.cu:1062`（env→bit）、`:193`（pad）、`:234`（dp4a）；A1 `src/kernels/cuda/native_router.cu:287`（ROUTE_DPP）；A5 `src/kernels/cuda/kv_q8.cu:158`（pre75_q8_gather）；A4 `build.ninja` 三边 FLAGS。

## 3. 边界（不冒充完成）

- 判否四项的开关与二进制全部在册（`r103x`/`r103ilp`，strings 门 5/5），可复测不重做。
- R114（B4）/R113（mmq）/R110·R112（PV-dot8）/R111（GPU runner）/R107（audit 17 轮）未动。
- 停机 ~2100 s 全部为测量窗；装机段 ~45 s。

门状态：deploy_gate **七条全 PASS**（D3b Δ=−1.37% vs 2×CV=0.17%；D4 锚门 4 点 0 坏例 + build_floor_bitident；D5 仅 +1 env；D7 run 4238161670）；报告三门 / 方案 / 账本 / round_ledger 见收工行；唯一 FAIL 仍为既存 `audit_scope`。
