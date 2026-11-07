#!/usr/bin/env python3
"""W1031: write R100 (+ three source entries) into the authoritative plan and the progress ledger.

Rules honoured: backup first; PROGRESS.tsv is tab-separated with 10 columns; every R in §6.2/§6.5 must
have a PROGRESS row (tools/plan_lint.py D) and every open PROGRESS id must appear in the plan (A/B).
"""
import io, shutil, time, os

WS = r"D:/workbuddy_space/strata_ws"
PROG = os.path.join(WS, "deploy/PROGRESS.tsv")
PLAN = os.path.join(WS, "deploy/W832_OPT_PLAN_V2.md")
TS = time.strftime("%Y%m%d_%H%M%S")

shutil.copy2(PROG, PROG + ".bak_w1031_" + TS)
shutil.copy2(PLAN, PLAN + ".bak_w1031_" + TS)

# ---------------------------------------------------------------- PROGRESS
rows = [
    ("B8工程", "R100",
     "llama.cpp 整树升到 v0.9.0（b12110 / ggml 0.29.0）：面核实 → 1115 条评审 → 3 TU 适配 → 门",
     "W1031", "count", "5", "4", "OPEN",
     "**W1031 立**：S1 面核实（我们只编 26 个 MMQ TU + ggml-base 9 + ggml-cpu 16，其余 1002 条 commit 的面一行不编）；"
     "S2 41 条逐条判定（`IN` 1 = #29478 `__vsub4`；`NUM` 1 = #31247 Q8_1 修正和，Q4_K/Q5_K 是 DS4 所以生效；"
     "`CHK` 4；其余 35 条有源码级惰性/不适用证明）；S3 适配 3 TU 4 处（`prec_src1`、`mul_mat_q_case<T,prec>`、"
     "`new_pool_for_device` 静态化）→ `NINJA_RC=0`，44,175,504 B，md5 `e0edacb74b037ff41895f3a57bcbc62e`；"
     "S4 门（`strata-0.1.57-004`，已回滚）：prefill@2K **512.28 vs 531.4–534.3（−3.6~−4.1%，CV 0.48% ⇒ 7×CV）**、"
     "@8K **685.48 vs 715.7–716.0（−4.3%）**、decode 34.91 vs 34.6–34.8（平）、ttft 4.07 vs 3.94（+3.3%）；"
     "贪心指纹 **1/3**（en2k 逐字节同；short 前 118 字符同、尾多 4 字符；**zh2k 从第 0 字符起 content 里出现 reasoning**）。"
     "⇒ 结论：整树升级**编译已通、门不过**，R99 判否的是 S1 手写 tile_spec，不是整树升级。",
     "deploy/W832_OPT_PLAN_V2.md §6.2 R100"),
    ("B8工程", "P376",
     "上游 llama.cpp 编译面核实：1115 条 commit 里只有 41 条碰我们编的文件，1002 条（89.9%）与我们无关",
     "W1031", "count", "1", "1", "DONE",
     "**W1031 立**：证据 `build-r28/build.ninja` —— `strata_mmq` 26 TU（13 个上游 mmq-instance + 6 个 tq + "
     "`quantize.cu` + 6 个自研）、`ggml-base` 9 TU、`ggml-cpu` 16 TU；`ggml-cuda/*.cu` 除 `quantize.cu` 与 mmq 实例"
     "外**一个都不编**（我们的 GPU 计算全在 `src/kernels/cuda/*.cu` 97 个自研内核里）。分类：A_mmq 41 / B_cpu 40 / "
     "C_core 32 / D_other 1002。脚本 `albus/w1031/triage.py`。",
     "deploy/W832_OPT_PLAN_V2.md §6.2 R100"),
    ("B8工程", "P377",
     "41 条 A 类逐条判定：真能执行 4 条，其中 1 条改数值；35 条有惰性/不适用证明",
     "W1031", "count", "1", "1", "DONE",
     "**W1031 立**：`IN` #29478（`__vsubss4`→`__vsub4`，改 `mmq-load-tiles.cuh` 的 Q6_K 两分支与 Q4_K，语义逐字节相同）；"
     "`NUM` #31247（Q8_1 修正和 `Σx`→`d·Σq`，Q4_K/Q5_K 的 `ds_layout=DS4` 所以生效）；`CHK` 4 条（#30837 的 "
     "`I%warp_size` 断言在 gfx906 上恒过：GCN 表 `I∈{64,128}`、warp=64）；`INERT` 3 条有铁证（#30553 stream-k 封顶——"
     "`mmq-config-gcn.cuh:120-127` 全 `stream_k=false`；#30517 MMVQ——`mmq-vec-dot.cuh` 对 K-quant 不调 `vecdotq` 的 "
     "mmvq 函数；#29927/#29193 等只对别家架构）；`NA` 其余（NVFP4/fp8/musa/graph/新 op/需改布局的融合）。"
     "全表在 `albus/w1031/R100_COMMIT_REVIEW.md` §3。",
     "deploy/W832_OPT_PLAN_V2.md §6.2 R100"),
    ("B8工程", "P378",
     "0.9.0 的编译断点只有 3 个 TU / 4 处 API，改完即编过；`x_gate`/`glu_op` 的担心不成立",
     "W1031", "count", "1", "1", "DONE",
     "**W1031 立**：断点 = `moe_mmq.cu`（`ggml_cuda_mmq_get_config` 要第 5 参 `prec_src1`、`mul_mat_q_case<T>` 要第 2 参）、"
     "`ggml_cuda_host.cu`（`new_pool_for_device` 变 static 且收 `ctx&`）、`mmq_nvfp4_w4a{4,8}.cu`（重命名后的 case 模板）。"
     "改法：恒 `GGML_PREC_Q8`（W4A4 用 `GGML_PREC_Q4`），与 0.9.0 的 `mmq.cu` 一致。补丁 `albus/w1031/adapt_v090.py`，"
     "源码副本 `~/strata166/w1031/src-v090`（生产树未动），构建 `build-v090`（141 s，ccache 命中）。",
     "deploy/W832_OPT_PLAN_V2.md §6.2 R100"),
    ("B8工程", "P379",
     "0.9.0 的门：prefill −3.6~−4.3%（7×CV）、decode 平、贪心指纹 1/3 ⇒ 不采纳",
     "W1031", "count", "1", "1", "DONE_NEG",
     "**W1031 立**：同 cfg_apply 协议、同配置、同一晚（基线 19:49 与 01:56/02:48 两臂）：2K **512.28**（CV 0.48） vs "
     "**534.28 / 531.56 / 531.42**；8K **685.48**（CV 0.09） vs **715.72 / 715.98**；decode **34.91** vs 34.75/34.61"
     "（r99-s0 的 36.84 是离群臂，不参与判定）；ttft 4.07 vs 3.94。指纹：en2k 224/224 全同；short 118/122（第 118 字符后"
     "多 4 字符）；**zh2k 7/81，第 0 字符起 content 里就是 reasoning 文本**⇒ 不是数值噪声，是 content/reasoning 分区变了。"
     "已 `rollback --exe strata-0.1.57-001`，health ok。",
     "deploy/W832_OPT_PLAN_V2.md §6.2 R100"),
    ("B8工程", "P380",
     "0.9.0 的两个疑点待定位：prefill −4% 的来源（MMQ DS4 修正和 vs ggml-cpu 主机侧）、zh 的 content/reasoning 分区为何变",
     "W1031", "count", "1", "0", "OPEN",
     "**W1031 立**：① 4% 归因：候选家族 A = `quantize_mmq_q8_1` 的 DS4 分支多算一次整数和（#31247，我们 Q4_K/Q5_K 正好走 DS4）；"
     "候选家族 B = `ggml-cpu` 主机侧（`STRATA_PREFILL_CPU_SHARE=auto/3072` 的 CPU share 走 host matmul，0.9.0 的 "
     "`tiled`/AVX2 路径与 pin 不同）。判定法：H1 = 0.9.0 树 + 手写回退 #31247 的 DS4 分支，单臂 A/B；若 4% 回来说明是 A，"
     "否则做 H2（ggml-cpu 只换回 pin 的 TUs）。② 分区变化：查同一 zh 请求的 token id 与 GGUF 的 "
     "`tokenizer.chat_template`/`token_type` 是否被 0.9.0 的 gguf 读法改变（这关系到 serve 层兼容，不只是数值）。",
     "deploy/W832_OPT_PLAN_V2.md §6.2 R100"),
]

with io.open(PROG, "a", encoding="utf-8") as f:
    for r in rows:
        assert len(r) == 10, r[1]
        f.write("\t".join(r) + "\n")
print("PROGRESS: appended", len(rows), "rows")

# ---------------------------------------------------------------- PLAN §6.2
ent = (
"| **R100** | **llama.cpp 整树升到 v0.9.0（b12110 / ggml 0.29.0）** | W1031：1115 条 commit 评审 | "
"**S1–S4 已做，门不过**：面 = 26 MMQ TU + ggml-base 9 + ggml-cpu 16（其余 1002 条的面一行不编）；"
"41 条逐条判定见 `albus/w1031/R100_COMMIT_REVIEW.md` §3；适配 3 TU / 4 处 API 后 `NINJA_RC=0`（44,175,504 B / `e0edacb7…`）；"
"门：2K **−3.6~−4.1%**（7×CV）、8K **−4.3%**、decode 平、指纹 **1/3**（zh 的 content/reasoning 分区变了） | "
"S5：把 4% 归因到 A（#31247 的 DS4 修正和）还是 B（ggml-cpu 主机侧）：H1 回退 DS4 分支单臂 A/B，再 H2 换回 pin 的 ggml-cpu TUs | "
"已完成 1.5 h；S5 约 40 min |\n"
"| **R101** | **`#31247` Q8_1 修正和 `Σx` → `d·Σq`**（只对 DS4 的 Q4_K/Q5_K 生效） | 上游 `8fc0376`（2026-11-03） | "
"未单独测；它随 0.9.0 进了 R100 的臂，所以 R100 的数值差里可能含它。单条 cherry-pick 到 pin 要同时改 `quantize.cu` 的 "
"`quantize_mmq_q8_1` DS4 分支 | 提示侧 KL ≤0.0139 + 48-token 贪心指纹逐字节；2K/8K 速度 | 20 min |\n"
"| **R102** | **`#29948`/`#31188` FFN/MoE gate/up+GLU 融合（要 gate/up 行交错布局）** | 上游 `c49edf0`/`f5222f2` | "
"未做。属**格式变更级**：改 pack 的 gate/up 行交错；我们 `moe_fused*.cu` 已是自家融合，收益上限要先算 | "
"上限 > 2×CV 才做；先算后改 | 估 1–2 天 |\n"
)

plan = io.open(PLAN, encoding="utf-8").read()
anchor = "\n#### 6.2.1 配置 / 环境面条目"
assert plan.count(anchor) == 1, plan.count(anchor)
plan = plan.replace(anchor, "\n" + ent.rstrip("\n") + "\n" + anchor, 1)

# ---------------------------------------------------------------- PLAN §6.5 note
head = "### 6.5 队列（**唯一排序处**；条目定义在 §6.2 / §6.2.1，不在这里重复）\n"
assert plan.count(head) == 1
note = (head + "\n> **2026-11-06 重排（W1031）**：**R100-S5 插到最前**——0.9.0 已证明能编、能跑、prefill 慢 4%，"
        "这 4% 是「上游变慢」还是「我们的 DS4 修正和变慢」决定后面所有与升级有关的账；它只花一次构建 + 一次 A/B，"
        "却能把 R51/R101 的优先级一次排清。R101 与 R100-S5 同源，跟着走。\n")
plan = plan.replace(head, note, 1)

io.open(PLAN, "w", encoding="utf-8").write(plan)
print("PLAN: R100/R101/R102 inserted, §6.5 note added")
