# -*- coding: utf-8 -*-
"""W946: add R88 (async staged copies) and R89 (QSA sparse-only prompt attention)."""
import io

P = "D:/workbuddy_space/strata_ws/deploy/PROGRESS.tsv"

R88 = ("**W946 立（2026-11-04 15:5x）**。外证：`sixvolts/llamacpp-gfx906-furnace`（同模型 177B MoE / UD-Q4_K_XL / 4xMI50）把 prompt 图输入改成"
       "pinned per-copy-slot 异步分阶段拷贝后，**llama-bench pp8192 877 -> 1978 t/s（+126%）**；它的诊断原文：host-synchronous copy 会等待该队列上已排队的跨设备等待，"
       "于是 scheduler 的图输入拷贝把设备串行化了。**本机对应事实**：prefill 的 `wait copy` 相位占 8.9-12.7%（AUDIT16 rep0 的三档），"
       "专家 blob 也走主机->GPU 上传（每 chunk 借 2606 槽 / 7.62 GiB）⇒ 端到端上限约 12.7%（不是 126%，我们不是全串行）。"
       "**第一步（零停服）**：从现有 DECODE_TIMING/服务端日志量每次 ubatch 的 wait-copy 绝对 ms 与同步点，判断是`排队等`还是`带宽`；"
       "若是排队（与 furnace 同因）才动调度；判据 |d|>=2xCV 且 prefill 六个长度档全不劣。")

R89 = ("**W946 立（2026-11-04 15:5x）**。外证：furnace 的 QSA prompt attention 在 context >= 3x selection 时**只读每行被选中的 key**，"
       "**pp4096 @48K depth 622 -> 1150 t/s（+85%）**（与更大 staging 合计）。本机对应：`qsa attn` 占 prefill 15-19%（W926）、"
       "每 token 仍读 2048 cell（W887 由 indexer.top_k=2048 推出 604 MFLOP/token）、有效算力 11-16% 峰；"
       "W926 的耗时指数 1.20 只证明`接近线性`，**没有证明`只读选中`**——scan 全 2048 cell 也是线性的。"
       "**第一步（零停服）**：读 `src/kernels/cuda/qsa_*_attn.cu`，确认 (a) 是否按 sparse index 逐 cell gather、还是按 dense 2048 扫；"
       "(b) mask/尾部是否每行重建。若已是 gather-only，本条并入 R46 的`拆三段`；若不是，这是 R85 里最大的一块。")

R85_ADD = (" 【W946】新增外证：furnace 同模型 QSA sparse prefill pp4096@48K **622->1150（+85%）** ⇒ R85 的 attn 方向有同形状落地案例；"
           "同时新增 R88（异步拷贝，furnace +126%）与 R89（QSA 只读选中 key）作为 R85 的两条并列手段。")

with io.open(P, encoding="utf-8", newline="") as f:
    lines = f.read().split("\n")

out, changed = [], []
for ln in lines:
    if "\t" in ln:
        f8 = ln.split("\t")
        if len(f8) >= 9 and f8[1] == "R85":
            f8[8] += R85_ADD; changed.append("R85"); ln = "\t".join(f8)
    out.append(ln)

while out and out[-1] == "":
    out.pop()

row88 = ["B5本机缺口", "R88",
         "prompt 路径异步分阶段拷贝：专家 blob / 图输入改 pinned per-slot 异步，消除 ubatch 间的设备排空（外证 furnace 同模型 pp8192 877->1978，+126%）",
         "W946 §6", "count", "1", "0", "OPEN", R88, "W946;furnace"]
row89 = ["B5本机缺口", "R89",
         "QSA prompt attention 只读选中 key（context >= 3x selection）：外证 furnace pp4096@48K 622->1150（+85%）；先确认我们是否已是 gather-only",
         "W946 §6", "count", "1", "0", "OPEN", R89, "W946;furnace"]

out.append("\t".join(row88))
out.append("\t".join(row89))
out.append("")

with io.open(P, "w", encoding="utf-8", newline="") as f:
    f.write("\n".join(out))
print("changed:", changed, "added R88/R89")
