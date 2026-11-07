# W1049 静态定案（不依赖窗口结果）

## B2 闭案（源码钉死，两棵树同一答案）

预填派发链（`prefill.cpp` ①②③④）在 gfx906 生产上的真实状态：

| 顺位 | 入口 | gfx906 状态 | 证据 |
|---|---|---|---|
| ① | `qsa_prompt_attn_batch_gated` | **编译都不编**：`#if defined(__HIPCC__) && !defined(STRATA_HIP_GFX906)`（qsa_prompt_attn.cu:2455 附近） | inspect_b2.txt |
| ② | `qsa_prompt_attn_batch` | **函数体首行 `#if defined(STRATA_HIP_GFX906) return false`**（注释自述「the FP32 kernel runs」指回退） | inspect_b2.txt gate region |
| ③ | `qsa_pattn_batch` | `STRATA_PATTN_BUILT=0`（qsa_pattn.cu:15，CUDA+SM60 专用） | inspect_b2.txt |
| ④ | `qsa_decode_attn_batch` 循环 | **实际热路径**（prefill.cpp 注释 "the decode kernel, 32 queries at a time"） | P435 |

⇒ **B2 的「prefill 分数用 dp4a」与 B1 同落一个模板**（`attn_chunk_kernel<M,*,*,*,OPT>`，OPT&2=int8 查询+`dot8_dp4a`，qsa_decode_attn.cu:195/234/306）。P435 说「预填吃 qsa_prompt_attn_batch」对 NVIDIA/sm75+ 成立、**对 gfx906 不成立**（①②③全拒）；W1046 的回退结论正确。

**B2 承诺的收益已兑现并入账**：P499（W1042）实测 `qsa attn` C vs B = **−10.9…−11.3%**（1K/8K/16K/20K），整条预填 GPU **−1.6…−2.8%**；P513（W1044）G1–G5 全过装机。**B2 = DONE（经 B1 同开关），不是丢失项**。旧排序「B2 > B3」按收益论已由 B3（HC down −24%）超越。

## OPT 位映射（生产 sha 03509d1b，qsa_decode_attn.cu:1062-1085）

| env | bit | 内容 | R103 项 |
|---|---|---|---|
| `STRATA_GFX906_ATTN_DPP=1` | 1 | softmax warp_sum/max 走 DPP xor 树 | **A3** |
| `STRATA_GFX906_ATTN_DP4A=1` | 2 | int8 查询 + dot8_dp4a 分数 | **B1=B2**（已装机） |
| `STRATA_GFX906_ATTN_LDS_PAD=1` | 4 | SQ_PAD=4/SP_PAD=1（列式 +1 pad） | **A2** |
| `STRATA_GFX906_ATTN_REDUCE12=1` | （模板位） | 12-in-16 打包归约（生产默认关） | **P457 探针** |
| `STRATA_GFX906_ROUTE_DPP=1` | — | router 三处归约换 DPP（r103x） | **A1** |
| `STRATA_GFX906_Q8_GATHER8=1` | — | Q8_1 8-wide gather（r103x） | **A5** |
| `STRATA_GFX906_ATTN_F16D/CTLREAD/F16Q` | 8/16/32 | 诊断位（r103x） | P457 剥离 |

**P457 混淆真存在且在产**：SWZ 派发宏固定 `attn_chunk_kernel<M,false,true,true,O>`（REDUCE12=true），而 ctl（OPT=0 且 env 未设 REDUCE12）跑 `<M,false,true>`（REDUCE12=false）。⇒ 生产 ATTN_DP4A=1 的收益/数值 = 「DP4A+REDUCE12」合体（W1044 门按合体判过，OK；归因仍需探针）。

## A 组源码事实

- **A1**（native_router.cu 144 行）：DPP xor1/2/4/8 + argmax_xchg，`STRATA_GFX906_ROUTE_DPP` 接线齐；「同操作数对同序 ⇒ bitwise」（源码注释 + xor 树与 shfl 树同形）。
- **A5**（kv_q8.cu 17 行）：8-wide 内核出 `STRATA_EXPERIMENTAL_SM60`、进 `STRATA_HIP_GFX906`；自述 bitwise（同 scale、同 `(float)code*scale→f16`）；decode 每层必经。
- **A2**：`OPT&4` 声明+索引 pad；外证 skyne98：列式 LDS 读 ld=32→33 得 1865→3974 GB/s（2.13×），CK 官方文档同结论（bank=(addr/4) mod 32）。
- **A3**：`OPT&1` 把 5 级 shfl_xor 换 xor1/2/8 DPP + 末级 shfl；同树同序 ⇒ bitwise。
- **A4**：逐 TU `-mllvm -amdgpu-sched-strategy=max-ilp`（qsa_decode_attn/qsa_pattn/fused_gr）；外证（onlybits MI50 指南）：ROCm 7.x clang 对 Vega20 调度回归，该 flag 恢复 prefill 10–20%；KI 报 FA +2~5% / MoE −2.2%（故逐 TU）。**非 bitwise ⇒ G2+G3**。

## 候选件（已构建，未装机）

- `strata-0.1.57-r103x` md5 `29194ee98f08588749a57c74592caf0c` / 43,806,992 B；分支 `gfx906/r103x@4a78f50ce`（= 03509d1b + 三文件取 91a7c5a4 内容）；strings 门 5/5（ROUTE_DPP/Q8_GATHER8/F16D/CTLREAD/F16Q）。
- `strata-0.1.57-r103ilp` md5 `c8b47b16a115eb19f6ea7e243962c576` / 43,761,784 B；分支 `gfx906/r103ilp@03509d1b` + build.ninja 三边 FLAGS 注入 max-ilp（root 才能写；首跑静默失败被 md5 撞车抓出——**同 md5 = 没生效**是有效门）。

## B4 / C 组边界（不丢）

- **B4**（GDN fp16 dot2）：PORT_PLAN 自定 defer「B1–B3 之后」；B3 已完 ⇒ 转 R114 候选，风险=bf16→fp16 丢指数范围，须 G2。本轮不实施。
- **C1**（V 侧 fp16 累加）、**C2**（int8 概率×int8 V dp4a）：C 组探索，k8v4 的 V 是 q4（C2 仅 int8 模式）；并入 R110/R112 的 PV 线或另立，不属 R103 移植面。
- **C3**（k8v4 V 旋转）：已实现，不动。
