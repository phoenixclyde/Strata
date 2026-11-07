#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# W1048: authoritative-plan writeback + queue rows (P534/P535/R113).
import io
import os

ROOT = r"D:/workbuddy_space/strata_ws"
os.chdir(ROOT)

# ------------------------------------------------- 1. W832 mmq verified facts
P = "deploy/W832_OPT_PLAN_V2.md"
s = io.open(P, encoding="utf-8").read()
old = "- **mmq（`P520`）**：K10 = llama.cpp 升 pin 的 **API 对齐**（#30168 等 25+5+1 处），`mmq*` 来自上游 `4c1004c`(10-19 **#30553**)；主体 b12180(11-06) ⇒ **混合树**，`mmq.cuh` 落后 5 提交（含 #30837 DP4A tile height，wave64 相关）。"
assert s.count(old) == 1
new = ("- **mmq（`P520`）**：K10 = llama.cpp 升 pin 的 **API 对齐**（#30168 等 25+5+1 处），`mmq*` 来自上游 `4c1004c`(10-19 **#30553**)；主体 b12180(11-06) ⇒ **混合树**，`mmq.cuh` 落后 5 提交——"
       "**W1048 GitHub API 逐条核实**（不凭印象）：`1a24df16`(10-23 **#30837** DP4A MMQ tile height 为 warp 整数倍，wave64/gfx906 直接相关)、"
       "`c49edf09`(#29948 FFN gate/up+GLU 融合)、`eb4e244b`(#31373 RDNA4_M，gfx906 无关)、`5ce06fc7`(#31296 NVFP4 融合)、`69ee2ecc`(#31047 MoE 数据布局线性化)；"
       "上游 `get_J_best()` 在 `ggml/src/ggml-cuda/mmq.cu`（本树 `moe_mmq.cu:386 pick_J()` 自己遍历）。择机移植立 **`R113`**，重编 + 数值门 + A/B，不盲跟。")
s = s.replace(old, new, 1)

# ------------------------------------------------- 2. W1048 回写 section
anchor = "### 回写 · W1047（2026-11-07 19:1x–22:3x）CI/CD 全覆盖回溯 + B3 干净门与真实模型门"
assert s.count(anchor) == 1
section = """### 回写 · W1048（2026-11-07 22:5x–23:5x）复核五条全量入方案 + 历史变更 CI/CD 回溯

- **复核五条 → 权威落点对照（全部可检索）**：① R103 移植面 → `R109`（B3 已装机 hc4b；A1/A5 待开）+ `P523` B2 死路径纠正；② dot4 硬件主力 → 本文 dot4 段（`strata_hip.h:237` 硬件 / `:246` 软回退，逐 TU 计数，`fused_gr` 真空已由 B3 填）；③ dot8 → `R91`+`R74`+`R110/R112`（k8v4 PV-dot8），预注册三步走不变；④ mmq 升 pin → `P520`+**`R113`**（本轮 API 核实 5 提交清单 + `get_J_best`）；⑤ CI/CD → `P521/P529–P532` + 本轮 `P534/P535`。任何后续调优只认这张对照表，不再另立口径。
- **历史变更 CI/CD 回溯（`P534`）——不是清单是执行**：14 个项目提交（port-all 7 + lcpp-k10 2 + attn/dot48/hc-dp4a 5）+ 4 个 ci 提交全部有 Downstream gate run=success。缺 run 的 10 个 ref 本轮补 `workflow_dispatch`：`fa8e6761`/`79516b21`/`8b44f3d1`/`806a4b2f`/`3b935ddf`/`8b5e547f`/`62d10e25`/`91a7c5a4`/`064aa6c0` + `pa4-recon`（run 42384609225–42385018433 段全绿）。三个「未提交补丁」的精确处置：**pa4** 用 `pa4_patch.py` 在 `8b5e547f` 上逐字重建（`ci/retro/pa4-recon@e36f0889`）；**pa7** 用 `pa6_patch→wire_f16d→pa7_patch` 在 `62d10e25` 累积重放，**与已提交 `91a7c5a4` 逐字节相同**（「未提交」实为「当时未提交、内容原样落进 91a7c5a4」）；**pa2** 补丁锚点与任何已提交态都对不上，精确树判不可恢复，登记豁免、内容落点=`3b935ddf`（run 42384985902）。UNTRACKED 43 件（0.1.53–0.1.56）与 `010`（0.9.0 树）永久豁免，md5 保留可验尸。
- **覆盖账与硬门（`P535`）**：`deploy/CI_RUNS.tsv` 为唯一覆盖账（sha→run/exempt）；`deploy_gate` 增 **D7 CI 证据**——装机 exe 的构建 sha 必须有 run=success 或显式豁免行，fail-closed（表缺/行缺 = REFUSE 而非 SKIP），负向自测 14/14。`artifact_ledger` 回填 run 绑定 14 件并修正 pa2/pa5/pa7 装机注记。
- **复核纠错留痕**：(a)「pa5 提交」就是 `62d10e25`（`commit_pa5.sh` 逐字），旧账写得像无名提交；(b) pa7 不是「62d10e25+单补丁」而是 pa6+wire_f16d+pa7 三连，重放证明即 `91a7c5a4`；(c) 轮询脚本被 GitHub 502 打断不影响已触发 run，补轮询收齐——工具要有断点续收，不算产品缺陷。
- **边界**：本轮回溯全程零停机、生产零变更（仍 `hc4b`/`9e2df560`）；`R111` GPU runner 仍 0；`R107` audit 欠账仍在。mmq 五提交只入方案不实施，实施属 `R113`。

"""
s = s.replace(anchor, section + anchor, 1)

# ------------------------------------------------- 3. directory row
dir_anchor = "| `回写 · W1047 装机补记（2026-11-07 22:3x）hc4b 落生产` | D1–D6 后换件；重启 7 / 停机 1810 s | W1047 |"
assert s.count(dir_anchor) == 1
row = "| `回写 · W1048（2026-11-07 22:5x–23:5x）复核五条全量入方案 + 历史变更 CI/CD 回溯` | 10 retro run 全绿；pa7 重放==91a7c5a4；D7 硬门 | W1048 |"
s = s.replace(dir_anchor, dir_anchor + "\n" + row, 1)
io.open(P, "w", encoding="utf-8", newline="\n").write(s)
print("plan updated", len(s))

# ------------------------------------------------- 4. PROGRESS rows
P = "deploy/PROGRESS.tsv"
lines = io.open(P, encoding="utf-8").read().splitlines()
rows = [
    ["B10环境与版本", "P534", "历史变更 CI/CD 回溯执行：10 个 retro ref 全部补出 Downstream gate run；pa4/pa7 重建、pa2 豁免",
     "W1048", "count", "1", "1", "DONE",
     "**W1048 执行**。14 项目提交 + 4 ci 提交全覆盖；缺 run 的 10 个 ref 补 workflow_dispatch 全绿（42384609225–42385018433 段）。pa4=pa4_patch.py 逐字重建（ci/retro/pa4-recon@e36f0889）；pa7=pa6→wire_f16d→pa7 三连重放**与 91a7c5a4 逐字节相同**；pa2 精确树不可恢复→豁免+内容落点 3b935ddf。UNTRACKED 43 件+010 永久豁免（md5 可验尸）。见 CI_RUNS.tsv。",
     "P529;P530;P521", "KW:retro|pa7|91a7c5a4"],
    ["B10环境与版本", "P535", "deploy_gate D7 CI 证据硬门：装机 sha 必须有 run=success 或显式豁免，fail-closed",
     "W1048", "count", "1", "1", "DONE",
     "**W1048 立**。deploy/CI_RUNS.tsv 为唯一覆盖账；D7 查 exe 构建 sha→run/exempt，表缺或行缺=REFUSE 不是 SKIP；负向自测 14/14（含 D7 三例）。artifact_ledger 回填 14 件 run 绑定并修正 pa2/pa5/pa7 注记。防止再出 W1040/W1044 类无 CI 装机与 43 件 UNTRACKED 制品。",
     "P533;P534", "KW:D7|CI_RUNS|fail-closed"],
    ["B10环境与版本", "R113", "mmq 升 pin 二段：4c1004c 后 5 提交择机移植（#30837 wave64 DP4A tile height 首选），重编+数值门+A/B",
     "W1048", "count", "1", "0", "OPEN",
     "**W1048 立（P520 的后续实施线）**。GitHub API 核实 mmq.cuh 在 4c1004c 后有 5 提交：1a24df16(#30837 DP4A tile height=warp 整数倍，gfx906/wave64 直接相关，首选)、c49edf09(#29948)、eb4e244b(#31373 RDNA4 无关)、5ce06fc7(#31296 NVFP4)、69ee2ecc(#31047 MoE 布局)；上游 get_J_best() 在 mmq.cu 可替本树 moe_mmq.cu:386 pick_J()。逐条评估、单变量、换 mmq 必重编+数值门+A/B，不盲跟。",
     "P520;R91", "KW:get_J_best|#30837|5 提交"],
]
for r in rows:
    assert len(r) == 11 and all("\t" not in x for x in r)
    assert not any(l.split("\t")[1] == r[1] for l in lines if l.count("\t") >= 9), r[1]
    whole = " ".join(r)
    for kw in r[10].replace("KW:", "").split("|"):
        assert kw in whole, (r[1], kw)
    lines.append("\t".join(r))
io.open(P, "w", encoding="utf-8", newline="\n").write("\n".join(lines) + "\n")
print("progress rows added")
