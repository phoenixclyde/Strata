#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# W1052 landing: R115 correction (reject), R110/R112 verdict (reject, real P/V
# budget FAIL), R111 runner online + gpu-gate, R105 close (93-site ledger),
# R116 new (PV dot4 int8 candidate), R107 bump.
import io
import os
import re

ROOT = r"D:/workbuddy_space/strata_ws"
os.chdir(ROOT)

P = "deploy/PROGRESS.tsv"
lines = io.open(P, encoding="utf-8").read().splitlines()
rows = [
    ["B10环境与版本", "P556", "R115 更正判否：独立 swiglu 是 fallback——fused_swiglu_q81 默认 ON + native_down 生产真 ⇒ 走融合变体",
     "W1052", "count", "1", "1", "DONE",
     "**W1052**。追谓词三跳定案：① `shared_expert.cu:207` `fused_swiglu_q81_enabled()` = env 缺省即 ON（`v==nullptr || atoi(v)!=0`）；② `native_down = native && down_data && native_mmvq_supported(down_type)`，down_type ∈ {Q5_1(7),Q8_0(8)} ⊂ `native_mmvq.cu:3575` 支持名单 ⇒ 生产（--native 伞）恒真；③ ⇒ 单 token 与批量两路都走 `native_swiglu_quantize_q8_1`（swiglu+量化融合），`shared_expert.cu:9/24/63/65/239` 的独立 swiglu 仅存在于 fallback 分支。W1051 P555 的「残余」是只看见 fallback 行、没跟到谓词——更正。gemm+swiglu 一体化（c49edf09 形态）残余收益估计 <0.3%（shared n_ff 小、融合 pass 已单趟），登记不立项。",
     "P555;R115", "KW:fused_swiglu_q81|native_mmvq_supported|fallback"],
    ["B10环境与版本", "P557", "R110/R112 判否：真实 P/V dump 误差预算 FAIL——P(int4)×V(int4) rel-rms 4.60%（22 记录/12804 P 值），不接 OPT",
     "W1052", "count", "1", "1", "REJECTED",
     "**W1052**。① 探针工程：`attn_chunk_body`（qsa_decode_attn.cu:125）softmax 后 PV 前插 env 门控一次性捕获（`STRATA_PV_DUMP`），dump kernel-local `sp[h][c]`（= dot8 方案要量化的 P）+ 原始 Q4_0 V 块 + srow；探针二进制 `strata-0.1.57-pvprobe`（gfx906/pvprobe@d0ea57396，md5 df8813f7，生产未装）。② 真实请求 dump：22 记录（64-cell chunk×12 头）/ 12,804 P 值 / 67,584 输出；P 分布长尾：min 3.6e-7、中位 8.0e-3、90 分位 0.166、峰值恒 1.0（chunk-local exp(a-m)）。③ 误差预算（R110 规格：P*Vscale 按 8-cell 组量化 int4、V nibble−8、int32 按组转 fp32）：**rel-rms 4.5951%**、max_abs 0.83（最差点 ref −10.26→−9.43，8% 级）；合成上界 6.23% 只略悲观，真实分布无红利 ⇒ 误差无预算（对照：KV8 采纳线 logits KL 0.0139、内核换代 1e-4 级）。**判否，PV-dot8 不接 OPT**。int4 按组量化的死因 = P 长尾（组 scale 取 max/7 时尾部 cell 直接变 0）。→ R116（P int8/dot4 路线）。",
     "R110;R112;P550", "KW:4.60|P(int4)×V(int4)|pvprobe"],
    ["B10环境与版本", "P558", "R111 上线：self-hosted GPU runner strata166-gfx906 online + gpu-gate 首跑落 runner（安全边界自定义并登记）",
     "W1052", "count", "1", "1", "DONE",
     "**W1052**。① runner v2.338.2 装于 166：专用用户 `ghrunner`（render 组进 GPU、sudoers.d 仅放行 `/usr/bin/docker`），systemd 服务 `actions.runner.phoenixclyde-Strata.strata166-gfx906` active，API 实证 `online`，labels `self-hosted,linux,x64,gfx906`。安装件经官方 sha256 `baebf204…7c40` 校验（gh-proxy 镜像 29.5MB/s 拉取——GitHub 直连 228MB 包在 166 只有 ~25KB/s）。② `gpu-gate.yml`（`.github/workflows/`，commit 702c6efbf）：**label 隔离**（`runs-on: [self-hosted, gfx906]`）+ **push/workflow_dispatch 仅**。③ 安全边界（本仓 PUBLIC，通用建议是公开仓禁挂 runner）：实际攻击面=有写权限者（PR 触发向量被「无 pull_request 触发」封死，工作流内注释立规）；残余风险=写权限账号被攻破=166 执行代码，登记备查；可选加固=转 private / ephemeral runner。④ 首跑 42449959915 在 runner 上 `Set up job` success（checkout 慢=CN→GitHub 网络，非 runner 故障）。",
     "R111;P521", "KW:strata166-gfx906|ghrunner|gpu-gate"],
    ["B10环境与版本", "P559", "R105 收口：93 处 STRATA_HIP_GFX906 五类总账——真硬件缺口仅 3 处且无生产损失",
     "W1052", "count", "1", "1", "DONE",
     "**W1052**。全树枚举 93 处（src+include+third_party），按三问（硬件能力 vs API？可运行时替代？生产可达？）分五类：A 正向门 60（为 gfx906 写的优化，维护过）；B 硬件事实 3（permlanex16 `s26_tsum.cuh:14`、wave32 族 `verify_kernels.cu:832`、pre75/DPP `qsa_decode_attn.cu:466`）；C 撰写假设/可选开关被编译掉 8（5 已点名：mtp:486/verify:1213/generate:3078+3371 可零风险解开见 §2、expert_cache:101 注释自证恒 discrete；另 3 不可达/不是缺口）；D API/平台分工 16；E 构建开关/无关 6。产出落 `albus/w1039/GFX906_GATES.md §5`。⇒ 能力清单 = B3 + C5，B 类均不损失生产功能。",
     "R105;P479;P480", "KW:93 处|五类总账|GFX906_GATES"],
    ["B10环境与版本", "P560", "R115 残余观察记档：gemm+swiglu 一体化预期 <0.3%，不立项",
     "W1052", "count", "1", "1", "DONE",
     "**W1052**。c49edf09 形态（GLU 折进 matmul epilogue）对本树 shared expert 的残余机会评估：swiglu+量化已融合为单趟（`native_swiglu_quantize_q8_1`），再折进 `native_mmvq` epilogue 只省一次 launch+一趟 gate/up 缓冲读写；shared n_ff ≈ 1280 量级、router+shared 相位 8K 共 271 ms，估计收益 <0.3% 量级且要动 mmvq 内核——登记不立项（列 REF）。R115 关。",
     "P556;R115", "KW:epilogue|<0.3%|REF"],
]
for r in rows:
    assert len(r) == 11 and all("\t" not in x for x in r)
    assert not any(l.split("\t")[1] == r[1] for l in lines if l.count("\t") >= 9), r[1]
    whole = " ".join(r)
    for kw in r[10].replace("KW:", "").split("|"):
        assert kw in whole, (r[1], kw)
    lines.append("\t".join(r))

closed = {}
for i, l in enumerate(lines):
    f = l.split("\t")
    if len(f) < 11:
        continue
    rid = f[1]
    if rid == "R115" and f[7] == "OPEN":
        f[2] = "R115：shared_expert gate/up+swiglu 融合——判否（独立 swiglu 是 fallback，见 P556）"
        f[6] = "1"; f[7] = "DONE"
        f[8] = "**W1052 结案·判否**。fused_swiglu_q81 默认 ON + native_down 生产真 ⇒ 融合变体已在跑；残余 gemm+swiglu 一体化 <0.3% 登记 REF（P560）。"
        f[10] = "KW:R115 判否|P556|fallback"
        lines[i] = "\t".join(f); closed["R115"] = 1
    if rid == "R110" and f[7] == "OPEN":
        f[2] = "k8v4 V 侧 dot8 原型——判否（真实 P/V 误差预算 FAIL，P557）"
        f[6] = "1"; f[7] = "DONE"
        f[8] = "**W1052 结案·判否**。合成 1.483× 真实但真实模型 P 分布下 P(int4)×V(int4) rel-rms 4.60% 无预算；int4 按组量化被 P 长尾杀死。dot8q≠dot8 的规格教训在册（W1046）。后续路线转 R116。"
        f[10] = "KW:R110 判否|P557|dot8"
        lines[i] = "\t".join(f); closed["R110"] = 1
    if rid == "R112" and f[7] == "OPEN":
        f[2] = "R110 的真实模型 P/V dump——已执行（22 记录），误差预算 FAIL（P557）"
        f[6] = "1"; f[7] = "DONE"
        f[8] = "**W1052 结案**。dump 探针 + 22 记录/12804 P 值实测：rel-rms 4.60%（合成上界 6.23%），P 分布长尾实证（中位 0.008/峰值 1.0）。判决：不接 OPT。"
        f[10] = "KW:R112 结案|P557|4.60"
        lines[i] = "\t".join(f); closed["R112"] = 1
    if rid == "R111" and f[7] == "OPEN":
        f[2] = "GPU CI runner——上线（strata166-gfx906 online + gpu-gate 落 runner，P558）"
        f[6] = "1"; f[7] = "DONE"
        f[8] = "**W1052 结案**。runner v2.338.2 systemd 常驻、API online、gpu-gate.yml label 隔离首跑落 runner；安全边界（公开仓无 PR 触发 + 专用用户 + docker-only sudo）自定义并登记。后续 job 扩展（ci/build.sh、A/B、binary_integrity/recipe）为增量工作，不阻塞收口。"
        f[10] = "KW:R111 结案|P558|strata166-gfx906"
        lines[i] = "\t".join(f); closed["R111"] = 1
    if rid == "R105" and f[7] == "OPEN":
        f[2] = "gfx906 能力清单——收口（93 处五类总账，P559）"
        f[6] = "1"; f[7] = "DONE"
        f[8] = "**W1052 结案**。GFX906_GATES.md §5 五类总账：真硬件缺口 3（无生产损失）+ 可翻案假设 5（已点名）。"
        f[10] = "KW:R105 结案|P559|93 处"
        lines[i] = "\t".join(f); closed["R105"] = 1
    if rid == "R107":
        f[2] = re.sub(r"W1032–W10\d\d \*\*\d+ 轮连续未审\*\*", "W1032–W1052 **21 轮连续未审**", f[2])
        f[8] = re.sub(r"W1032–W10\d\d", "W1032–W1052", f[8])
        f[10] = "KW:AUDIT29|21 轮连续未审|audit_scope"
        lines[i] = "\t".join(f)
assert len(closed) == 5, closed

r116 = ["B10环境与版本", "R116", "R116：PV dot4 路线（P int8×V int8，V nibble→int8 无损）——R110 判否后的唯一残路，先合成误差预算",
        "W1052", "count", "1", "0", "OPEN",
        "**W1052 立项**（P557 尾）。P(int4) 死于长尾（组 scale max/7 把尾部 cell 置 0）；int8 量化 P（128 级）误差 ~16× 小（预期 rel-rms ~0.3% 级），V 的 Q4_0 nibble→int8 符号扩展**无损**，硬件走 `v_dot4_i32_i8`（本树主力指令）。代价：V 读流量 ×2（nibble→byte）。验收顺序沿 R110：合成误差预算（用 w1052 的 22 记录真实 P/V 重放）→ 微基准（同访问面）>1.3× → 才谈 OPT 位。零停机离线先行。",
        "P557;R110", "KW:R116|v_dot4_i32_i8|P int8"]
assert not any(l.split("\t")[1] == "R116" for l in lines if l.count("\t") >= 9)
lines.append("\t".join(r116))
io.open(P, "w", encoding="utf-8", newline="\n").write("\n".join(lines) + "\n")
print("W1052 progress: P556-P560, R105/110/111/112/115 closed, R116 opened, R107=21")
