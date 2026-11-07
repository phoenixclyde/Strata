import io, time
TS = time.strftime("%Y-%m-%d %H:%M")
P = "D:/workbuddy_space/strata_ws/deploy/PROGRESS.tsv"
lines = io.open(P, encoding="utf-8").read().splitlines()
out = []
for l in lines:
    c = l.split("\t")
    if len(c) > 8 and c[1] == "R95":
        c[8] = (c[8] or "") + (
            " 【W992 候选 A 否决 %s】查四张架构表：Q4_K 的 J **在所有架构上都从 64 起**"
            "（CDNA 128、Ampere 128、RDNA3 64/128、GCN 64/128）⇒ 不是 GCN 缺表行，而是 K-quant 的 tile 宽度下限就是 64。"
            "**A（启用 J<64）作废**，不再浪费编译时间。余下：B 小专家走 small-M/GEMV 分流；C dequant 融合。" % TS)
        l = "\t".join(c)
    out.append(l)
io.open(P, "w", encoding="utf-8", newline="").write("\n".join(out) + "\n")
print("PROGRESS: R95 候选 A 否决")
