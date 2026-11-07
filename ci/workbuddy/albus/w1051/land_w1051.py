#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# W1051 landing: R113 close (4 commits judged), R114 G2 verdict (reject install),
# R115 new, determinism methodology finding, W832 writeback, R107 bump.
import io
import os
import re

ROOT = r"D:/workbuddy_space/strata_ws"
os.chdir(ROOT)

# ------------------------------------------------ PROGRESS
P = "deploy/PROGRESS.tsv"
lines = io.open(P, encoding="utf-8").read().splitlines()
rows = [
    ["B10环境与版本", "P551", "R113 余 4 提交逐个判决（全部判否）：RDNA4_M/NVFP4/MoE-tile_spec 与本树无关或冲突；#29948 融合已被 s2_expert_grouped 覆盖",
     "W1051", "count", "1", "1", "DONE",
     "**W1051**。GitHub API 逐条取真实 diff 判决：① eb4e244b（#31373 RDNA4_M gfx1170/1171）判否——全部改动门在 RDNA4_M 宏下，GCN 路径零变化；② 5ce06fc7（#31296 NVFP4 gate/up+GLU 融合）判否——Blackwell NVFP4 特性，本树 mmq_nvfp4_w4a4/w4a8 虽在但模型是 Q4_K、路径未启用（若 R74 W4A4 线启用可参考形态）；③ 69ee2ecc（#31047 MoE tile_spec 线性化）判否——改 mmq.cuh write_back 签名（get_rows_to_sorted→ids_dst）会破坏本树 moe_mmq 契约（src/prefill/moe_mmq.cu 25 处），且 ncols_opt 无条件化只对 ggml_cuda_mul_mat_q 生效（本树不走）；④ c49edf09（#29948 gate/up+GLU 融进 MMQ）判否——本树已覆盖：s2_expert_grouped.cu 注释明示 silu(gate)*up 在融合内核 epilogue（swiglu.cuh）、standalone pass 已删、gate/up 行连续布局同构。R113 五提交全结（1a24df16 见 P549）。",
     "R113;P549;P520", "KW:#29948|s2_expert_grouped|#31047"],
    ["B10环境与版本", "P552", "R114 G2 prefill 门 + 派发链钉死：hc≡g0≡g1 逐位（KL 0.00000）；fused_gdn_ab 不在 prefill 批式路径",
     "W1051", "count", "1", "1", "DONE",
     "**W1051**。① 三对 pcompare 全部 KL mean/median/max=0.00000、top-1 100%：hc≡g0（r114 off 臂与生产 hc4b 逐位同，off 路径未扰动）、g0≡g1（DOT2 开关在 prefill 零影响）、hc≡g1。② 派发链源码钉死：fused_pre = g_fused_gdn && native_gdn_enabled() && native_bf16_projections && ssm_d_conv==4 && ssm_state_size==128（layer.cpp:282）；--native 伞开关置 native_bf16=native_gdn=true（generate.cpp:4405）⇒ 谓词真；但 layer.cpp 的 fused_gdn_ab 是**单 token 逐层**路径（decode），prefill 批式 alpha/beta 在 gdn conv+gates 相位（8K 46 ms）批式算，不走此内核 ⇒ prefill 零变动是结构性必然。③ gdn_ab_multi 仅 verify.cpp 用（生产不走）。",
     "R114;P550", "KW:fused_pre|qsa_decode|KL 0.00000"],
    ["B10环境与版本", "P553", "R114 G2 decode 性能门 FAIL：配对 +0.82%（2×SE 2.17%）与非配对 +2.39%（2×CV 6.8%）均不显著 ⇒ 不装机",
     "W1051", "count", "1", "1", "REJECTED",
     "**W1051**。g2b 非配对 n=6：a_off 52.92(cv2.46%) vs b_on 54.18(cv3.38%) = +2.39%，2×CV 6.8% 未过；g2c 配对设计（同 nonce 双臂，缓存不过重启已证）n=8：逐对 delta +4.88/-0.94/-2.37/+3.21/+3.80/-4.60/+2.06/+0.56%，均值 **+0.82%、2×SE 2.17%** 未过。曝光面数学自洽：微基准 1.33× 真实，但 decode 每步 ab 份额 ≈0.55 ms/18.9 ms ≈2.9%（gfx906 实测 7.65us/call×2 投影×36 层），预期端到端 ≈+1%，恰与 +0.82% 一致——收益真实但低于 2×CV 采纳线。prefill 相位（gdn 1154.3 vs 1155.7 ms，conv+gates 六次全 46/15 ms）零变动。per-row 2^k 缩放预案不适用（失败因收益不可检出而非精度）。留档复开条件：GDN 形状变化使 ab 占比上升、或与其它微收益打包同一次重编。",
     "R114;P552;P550", "KW:0.82|2xSE|不装机"],
    ["B10环境与版本", "P554", "R114 G2 decode 数值面 + 确定性对照：8/8 文本对早期翻（fp16 实证暴露）；同臂冷启 T1≡T3 逐位确定；缓存重放 T1≠T2（新铁律）",
     "W1051", "count", "1", "1", "DONE",
     "**W1051**。① g2c 8 对同提示贪心 600-token 文本：8/8 在 char 38–304 分歧（同义词级早期 argmax 翻转，之后自回归发散）；g2b 单对同结果（char 479 detect/identify）。② g2d 确定性对照（同提示 g2c-pair-1，a_off）：T1≡T3（两次冷启 bitwise 同，2402B 全等）⇒ harness 确定、翻转归因 dot2 的 fp16 噪声；T1 vs T4（跨臂）char 224 翻，与 g2c pair1 同位置复现（翻转位确定性）。③ **T1≠T2**：同会话缓存重放（cached_tokens=2092）与冷算路径不同值 ⇒ **数值门/A/B 对比禁止使用缓存命中数据，必须冷启**（新铁律入账）。性能已否，数值面留档：若将来打包采纳须先过 36 题答案门（W807/8 decode 传统）而非文本逐位。",
     "R114;P553", "KW:确定性|cached_tokens|8/8"],
    ["B10环境与版本", "P555", "举一反三：shared_expert 独立 swiglu 残余（routed 专家已融合）——R115 立项",
     "W1051", "count", "1", "1", "OPEN",
     "**W1051**。判 c49edf09 时顺藤摸瓜：routed 专家 gate/up+swiglu 已在 s2_expert_grouped.cu 融合 epilogue，但 **shared_expert.cu:402/441/443 仍有独立 swiglu_kernel<<<>>> 两形态**（swiglu_kernel 与 native_swiglu_kernel），即 shared 专家的 gate/up 与 GLU 未融合。shared 专家逐 token 全跑（router+shared 相位 8K 271 ms / 3.1%）。候选=把 swiglu 折进 shared 专家 gate/up 的 epilogue（照 s2 形态），预估小（GLU 本身是 elementwise）但形态已知、单开关可 A/B。R115 承载。",
     "P551", "KW:shared_expert|swiglu_kernel|epilogue"],
]
for r in rows:
    assert len(r) == 11 and all("\t" not in x for x in r)
    assert not any(l.split("\t")[1] == r[1] for l in lines if l.count("\t") >= 9), r[1]
    whole = " ".join(r)
    for kw in r[10].replace("KW:", "").split("|"):
        assert kw in whole, (r[1], kw)
    lines.append("\t".join(r))

n113 = n114 = nr115 = 0
for i, l in enumerate(lines):
    f = l.split("\t")
    if len(f) >= 11 and f[1] == "R113":
        f[2] = "mmq 升 pin 二段：5 提交全结（#30837 断言验证 + 4 提交逐个判否）"
        f[6] = "1"; f[7] = "DONE"
        f[8] = "**W1051 结案**。1a24df16 断言双插验证不变量成立（P549）；c49edf09/eb4e244b/5ce06fc7/69ee2ecc 真实 diff 逐个判否（P551）。残余真机会转 R115（shared_expert swiglu，P555）。"
        f[10] = "KW:R113 结案|P551|5 提交"
        lines[i] = "\t".join(f); n113 += 1
    if len(f) >= 11 and f[1] == "R114":
        f[2] = "B4 GDN fp16 dot2：G2 全跑（prefill 逐位 + decode 性能/数值/确定性）——性能门未过，不装机（P553）"
        f[6] = "1"; f[7] = "DONE"
        f[8] = "**W1051 结案·不采纳**。G2 prefill KL 0.00000 逐位（P552）；decode 配对 +0.82%±2.17% 不显著（P553）；decode 文本 8/8 早期翻、同臂冷启确定（P554）。微基准 1.33× 真实但暴露面 ≈+1% 级；候选 r114 与 gfx906/r114 分支留档，复开条件见 P553。缩放预案不适用。"
        f[10] = "KW:R114 判否|P553|d909d597"
        lines[i] = "\t".join(f); n114 += 1
    if len(f) >= 11 and f[1] == "R107":
        f[2] = re.sub(r"W1032–W1050 \*\*\d+ 轮连续未审\*\*", "W1032–W1051 **20 轮连续未审**", f[2])
        if "20 轮" not in f[2]:
            f[2] = re.sub(r"W1032–W10\d\d \*\*\d+ 轮连续未审\*\*", "W1032–W1051 **20 轮连续未审**", f[2])
        f[8] = re.sub(r"W1032–W10\d\d", "W1032–W1051", f[8])
        f[10] = "KW:AUDIT29|20 轮连续未审|audit_scope"
        lines[i] = "\t".join(f)
assert n113 == 1 and n114 == 1, (n113, n114)

r115 = ["B10环境与版本", "R115", "shared_expert gate/up+swiglu 融合（照 s2_expert_grouped epilogue 形态）：单开关 A/B，预期小",
        "W1051", "count", "1", "0", "OPEN",
        "**W1051 立项**（P555）。shared_expert.cu:402/441/443 独立 swiglu 遍是 c49edf09 判否时发现的真残余；shared 专家逐 token 全跑。先量独立 swiglu 占 router+shared 相位份额，再决定动不动手。",
        "P555;P551", "KW:R115|shared_expert|swiglu"]
assert not any(l.split("\t")[1] == "R115" for l in lines if l.count("\t") >= 9)
lines.append("\t".join(r115))
io.open(P, "w", encoding="utf-8", newline="\n").write("\n".join(lines) + "\n")
print("progress: P551-P555 + R113 closed + R114 rejected + R115 opened + R107=20")
