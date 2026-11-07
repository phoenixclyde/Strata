# -*- coding: utf-8 -*-
import io, time
TS = time.strftime("%Y-%m-%d %H:%M")

P = "D:/workbuddy_space/strata_ws/deploy/PROGRESS.tsv"
lines = io.open(P, encoding="utf-8").read().splitlines()
out = []
for l in lines:
    c = l.split("\t")
    if len(c) > 8 and c[1] == "R88":
        c[8] = (c[8] or "") + (
            " 【W990 归因改写 %s】**首块不是主机缝隙、也不是 CPU 池**：`STRATA_PREFILL_TIMING` 实测 "
            "2K: GPU timeline 3668 ms / wall 3683 ms（缝隙 15 ms）；16K: 19543/19665（122 ms）。"
            "差额在**每 token 成本**：1.784 vs 1.240 ms/tok，其中 gemm gate/up 0.482 vs 0.252（1.91×）、"
            "gemm down 0.299 vs 0.160（1.87×）、dequant 0.125 vs 0.032（3.9×）、wait copy 0.071 vs 0.005（14×）；"
            "qsa attn 反而 0.123 vs 0.216（小 prompt 更便宜）。⇒ 靶子改为**小批 GEMM/去量化效率**，不是预取。" % TS)
        l = "\t".join(c)
    out.append(l)

rows = [
    "\t".join(["B7配置旋钮", "P267", "`STRATA_PREFILL_TIMING=1`（prompt 路径分相位计时）", "W990", "count", "1", "1", "DONE",
               "**W990 开启（%s）**：每请求两行（26 相位 + 主机分解）。代价：TTFT 4.106 vs 4.074（+0.8%%，band 2.0%%）⇒ 在噪声内。"
               "这是 R88/R95 唯一的归因通道，保留。" % TS]),
    "\t".join(["B5本机缺口", "R95", "小批 GEMM 效率：2K prompt 时 gemm gate/up 与 down 的每 token 成本是 16K 的 1.9×", "W990", "count", "1", "0",
               "OPEN", "**W990 立（%s）**：2K 1.784 ms/tok vs 16K 1.240；差额 ≈1.1 s 全部落在 GEMM 与 dequant。"
               "候选：①每组专家的行数过小导致 tile 利用率低 ⇒ 查 MMQ 的 J/`ncols` 选择（`get_J_max` 家族）；"
               "②dequant 0.125 ms/tok 是 16K 的 3.9× ⇒ 小批时去量化没有摊薄；③wait copy 14× ⇒ 小批时每层同步占比高。"
               "判据：2K/8K/16K 三档同测，GEMM 相位 ms/tok 下降 ≥10%% 且 decode 不掉。" % TS]),
]
io.open(P, "w", encoding="utf-8", newline="").write("\n".join(out + rows) + "\n")
print("PROGRESS: R88 归因改写 + P267/R95")
