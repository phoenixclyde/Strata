import io, time
TS = time.strftime("%Y-%m-%d %H:%M")
P = "D:/workbuddy_space/strata_ws/deploy/PROGRESS.tsv"
lines = io.open(P, encoding="utf-8").read().splitlines()
out = []
for l in lines:
    c = l.split("\t")
    if len(c) > 8 and c[1] == "R95":
        c[8] = (c[8] or "") + (
            " 【W991 第一步 %s】**J 固定**：2K 请求 1,564 次 `pick_J` 全部选 **J=64**，而 ncols 分布 min 4 / p50 331 / p90 742 / max 7680 "
            "⇒ gfx906 上 <64 的 tile 配置不可用（`ggml_cuda_mmq_get_config` 返回 COUNT），小专家只填了 64 宽 tile 的一部分。"
            "长度曲线（GPU ms/tok）：2056 1.784 / 3058 1.571 / 4056 1.607 / 6058 1.441 / 9058 1.319 / 12057 1.276 / 15757 1.240 "
            "⇒ 单调收敛、**无台阶**（不是 wave 量化，更像 tile 填充率 + 每专家固定成本摊薄）。" % TS)
        l = "\t".join(c)
    out.append(l)
rows = ["\t".join(["B7配置旋钮", "P268", "`STRATA_MMQ_DEBUG_J=1`（打印每次 pick_J 的 ncols→J）", "W991", "count", "1", "1", "DONE",
                   "**W991（%s）**：仅观测，1,564 行/请求，已撤（不在生产）。用途：确认 J 选择。判据留档。" % TS])]
io.open(P, "w", encoding="utf-8", newline="").write("\n".join(out + rows) + "\n")
print("PROGRESS: R95 补 J 结论 + P268")
