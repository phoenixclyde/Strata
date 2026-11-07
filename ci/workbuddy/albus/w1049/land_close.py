#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# W1049: PROGRESS verdict rows + R109 close + R114 queue + W832 writeback.
import io
import os
import re

ROOT = r"D:/workbuddy_space/strata_ws"
os.chdir(ROOT)

# ------------------------------------------------ PROGRESS rows
P = "deploy/PROGRESS.tsv"
lines = io.open(P, encoding="utf-8").read().splitlines()
rows = [
    ["B10环境与版本", "P536", "A2 LDS_PAD 采纳：组合臂（DP4A+PAD）8K qsa attn 1103.7 vs 1119.0（−1.37%），双重 bitwise",
     "W1049", "count", "1", "1", "DONE",
     "**W1049 三窗实测**。G1 双重：pad 单独 f≡c、组合 e≡m 均 KL 0.00000（P457 探针后纯布局确认）。n=3 破缓存计时：8K qsa attn 组合 1103.7（cv0.09%）vs 现产 1119.0（−1.37%，2×CV 0.18%）vs 地板 1261.7（−12.5%）；2.5K 226 vs 230；decode 49.2 vs 50.3 持平。装机=config 加 STRATA_GFX906_ATTN_LDS_PAD=1（OPT=6）。见 P536 register。",
     "P512;P527", "KW:LDS_PAD|1103.7|e≡m"],
    ["B10环境与版本", "P537", "A1 ROUTE_DPP 判否：bitwise 证实但性能不可检出",
     "W1049", "count", "1", "1", "DONE",
     "**W1049**。r103x@4a78f50ce 移植 native_router 144 行 DPP（xor1/2/4/8+argmax_xchg，STRATA_GFX906_ROUTE_DPP）。f≡g KL 0.00000（同操作数对同序）。router+shared 271 vs 271 ms、decode 47 vs 49 tok/s：全部在噪声内，−0.3~0.6ms 预估低于相位分辨率。",
     "P536", "KW:ROUTE_DPP|f≡g|不可检出"],
    ["B10环境与版本", "P538", "A5 Q8_GATHER8 判否：bitwise 证实但 gather 相位仅 0.3%",
     "W1049", "count", "1", "1", "DONE",
     "**W1049**。kv_q8 8-wide gather 出 SM60 进 HIP_GFX906，strings 门 5/5。f≡h KL 0.00000（同 scale 同舍入证实）。gather 24-25 ms 持平、decode 50 vs 49。预填 gather 占比 0.3%，decode 层面亦无可测差。",
     "P536", "KW:Q8_GATHER8|f≡h|0.3%"],
    ["B10环境与版本", "P539", "A3 ATTN_DPP 判否：局部 −0.56% 显著但全条不显著",
     "W1049", "count", "1", "1", "DONE",
     "**W1049**。softmax DPP（OPT bit1）8K qsa attn 1255 vs 1261.7（−0.56%，2×CV≈0.2%），整条 GPU +0.45% 不显著；2.5K/decode 无差。P447 历史 −0.76% 同向复现。",
     "P536", "KW:ATTN_DPP|0.56%|全条不显著"],
    ["B10环境与版本", "P540", "A4 逐 TU max-ilp 判否：attn +39.6% 显著有害（与社区全局 flag 相反）",
     "W1049", "count", "1", "1", "DONE",
     "**W1049**。build.ninja 三边 FLAGS 注入（root 权限；首跑静默失败被 md5 撞车抓出）。a≡k KL 0.00000（调度 bitwise）但 8K qsa attn 1762 vs 1261.7（**+39.6%**）、整条 GPU +6.2%。社区 +10~20% 来自其他 TU（GEMM）；对 attn/fused_gr 逐 TU 是反向。若重试只试 gemm TU。",
     "P536", "KW:max-ilp|39.6%|gemm TU"],
    ["B10环境与版本", "P541", "P457 归约混淆结案：REDUCE12 无辜（KL=0），CTLREAD 推翻「手工读无辜」",
     "W1049", "count", "1", "1", "DONE",
     "**W1049 三段剥离**。① a≡d（REDUCE12 单独）KL 0.00000 ⇒ 归约无辜（P457 判据 KL=0 支）；② f vs i（CTLREAD=手工 K 读+晚 scale+基线算术）KL mean 0.0948 / max 0.367 / top-1 75% ⇒ OPT 路径 K 读/scale 应用是真实差异源，P457 的「KL==0 ⇒ 手工读无辜」预期被证伪；③ f vs j（F16Q）KL 0.0340 / top-1 100%。历史 DP4A KL 归因主体=int8 查询量化（P454），非 REDUCE12。",
     "P457;P453", "KW:REDUCE12|CTLREAD|0.0948"],
    ["B10环境与版本", "P542", "B2 落点闭案：四层派发全查，gfx906 走 ④，B2=B1 同模板且收益已兑现",
     "W1049", "count", "1", "1", "DONE",
     "**W1049 源码钉死**。① gated 编译排除（!STRATA_HIP_GFX906）② prompt_attn_batch 首行 return false ③ pattn STRATA_PATTN_BUILT=0 ④ qsa_decode_attn_batch=真热路径。B2 分数 dp4a 与 B1 同落 attn_chunk_kernel OPT&2（:234/:306）。P435 对 gfx906 不成立；W1046 回退结论正确。收益兑现 P499 −10.9~−11.3% + W1049 复证 1119 vs 1261.7。B2 非丢失项。",
     "P435;P499", "KW:qsa_decode_attn_batch|OPT&2|兑现"],
    ["B10环境与版本", "R114", "B4 GDN fp16 dot2：B1–B3 全结后转正为候选，须 G2（bf16→fp16 丢指数范围）",
     "W1049", "count", "1", "0", "OPEN",
     "**W1049 立（PORT_PLAN 的 defer 到期）**。fused_gdn.cu:115-118 现为 bf16 位拼接+fp32 fmaf；换 v_dot2_f32_f16 需权重先转 fp16（5 位指数 vs bf16 8 位）。GDN 占预填 ~13%。先离线权重转换 KL 门再动内核；与 R110 的 PV-dot8 不混。",
     "P536", "KW:v_dot2_f32_f16|bf16|GDN"],
]
for r in rows:
    assert len(r) == 11 and all("\t" not in x for x in r)
    assert not any(l.split("\t")[1] == r[1] for l in lines if l.count("\t") >= 9), r[1]
    whole = " ".join(r)
    for kw in r[10].replace("KW:", "").split("|"):
        assert kw in whole, (r[1], kw)
    lines.append("\t".join(r))

# R109 close
n = 0
for i, l in enumerate(lines):
    f = l.split("\t")
    if len(f) >= 11 and f[1] == "R109":
        f[2] = "R103 后续移植面执行线（W1049 全部收口：B3 已装、A1/A5/A3/A4 判否、A2 采纳、B2 闭案）"
        f[6] = "1"; f[7] = "DONE"
        f[8] = "**W1049 收口**。顺序执行完：B3（W1047 装机）→ A1（P537 判否）→ A5（P538 判否）→ A2（P536 采纳）/A3（P539 判否）→ A4（P540 判否）。B2 独立闭案（P542）。全部单开关、同地板、G1/G3 或 G2 门齐。"
        f[10] = "KW:R103 全收口|P536|P540"
        lines[i] = "\t".join(f); n += 1
assert n == 1, n

io.open(P, "w", encoding="utf-8", newline="\n").write("\n".join(lines) + "\n")
print("progress rows added, R109 closed")

# ------------------------------------------------ W832 writeback
P = "deploy/W832_OPT_PLAN_V2.md"
s = io.open(P, encoding="utf-8").read()
anchor = "### 回写 · W1048（2026-11-07 22:5x–23:5x）复核五条全量入方案 + 历史变更 CI/CD 回溯"
assert s.count(anchor) == 1
section = """### 回写 · W1049（2026-11-07 23:5x–01:1x）R103 移植面全收口：B2 闭案、A2 采纳、A1/A3/A4/A5 判否、P457 结案

- **B2 闭案（`P542`）**：gfx906 预填派发四层全查——① gated 编译排除（`!STRATA_HIP_GFX906`）② `qsa_prompt_attn_batch` 首行 `return false` ③ `STRATA_PATTN_BUILT=0` ④ `qsa_decode_attn_batch` 循环=真热路径。B2 的「prefill 分数 dp4a」与 B1 同模板（`OPT&2`，`qsa_decode_attn.cu:234/306`），W1044 已装且收益兑现（P499 −10.9~−11.3%，W1049 复证 1119 vs 1261.7）。P435 对 gfx906 不成立。**B2 不是丢失项。**
- **A2 采纳（`P536`）**：LDS +1 pad（`OPT&4`）。G1 双重 bitwise（pad 单独 f≡c、组合 **e≡m** 均 KL 0）；n=3 破缓存：8K qsa attn 组合 **1103.7 vs 1119.0（−1.37%）** vs 地板 1261.7（−12.5%），decode 持平。装机=config 加 `STRATA_GFX906_ATTN_LDS_PAD=1`。
- **判否四项（全部证据在册、可复测）**：A1 `ROUTE_DPP`（`P537`，bitwise✓ 但 router 相位 271vs271 不可检出）；A5 `Q8_GATHER8`（`P538`，bitwise✓ 但 gather 占 0.3%）；A3 `ATTN_DPP`（`P539`，qsa −0.56% 显著但全条不显著）；A4 逐 TU `max-ilp`（`P540`，bitwise 但 attn **+39.6%** 有害；社区 +10~20% 属 GEMM TU，勿全局抄）。
- **P457 结案（`P541`）**：REDUCE12 单独 KL=0 ⇒ 归约无辜；CTLREAD KL 0.0948/top-1 75% ⇒ 「手工 K 读+晚 scale 无辜」被证伪（真实差异源）；F16Q KL 0.034。历史 DP4A KL 归因=int8 查询量化（P454），非 REDUCE12。
- **B4 转正（`R114`）**：PORT_PLAN 的 defer 随 B1–B3 全结到期；GDN fp16 dot2 先过 bf16→fp16 离线 KL 门。
- **窗口口径**：三窗（主窗 8 计时臂+8 dump+7 pcompare、r103b 破缓存 n=3、r103c/d 组合臂+G1）累计重启 ~24 次、停机 ~2100 s；全部 trap 还原；生产只在本轮末尾装 A2 一处 env。
- **R103/R109 全收口**：移植面每项「已装或已判」，无悬空。

"""
s = s.replace(anchor, section + anchor, 1)
dir_anchor = "| `回写 · W1048（2026-11-07 22:5x–23:5x）复核五条全量入方案 + 历史变更 CI/CD 回溯` | 10 retro run 全绿；pa7 重放==91a7c5a4；D7 硬门 | W1048 |"
assert s.count(dir_anchor) == 1
row = "| `回写 · W1049（2026-11-07 23:5x–01:1x）R103 移植面全收口` | B2 闭案；A2 采纳；A1/A3/A4/A5 判否；P457 结案 | W1049 |"
s = s.replace(dir_anchor, dir_anchor + "\n" + row, 1)
# denominator
a = "| 进度分母 | **485 条 / 已结 391 / 80.6%**（W1048；"
assert s.count(a) == 1
s = s.replace(a, "| 进度分母 | **493 条 / 已结 398 / 80.7%**（W1049；")
io.open(P, "w", encoding="utf-8", newline="\n").write(s)
print("plan updated")
