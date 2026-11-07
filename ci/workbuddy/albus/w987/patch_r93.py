# -*- coding: utf-8 -*-
import io, time
TS = time.strftime("%Y-%m-%d %H:%M")

P = "D:/workbuddy_space/strata_ws/deploy/PROGRESS.tsv"
lines = io.open(P, encoding="utf-8").read().splitlines()
out = []
for l in lines:
    c = l.split("\t")
    if len(c) > 7 and c[1] == "R93":
        c[6] = "1"
        c[7] = "DONE"
        c[8] = (c[8] if len(c) > 8 else "") + (
            " 【W987 结案 %s】n=3/长度、每长度 CV 0.05–1.3%%：chunk **8192 vs 16384** ⇒ "
            "2K 511.96/511.73（+0.04%%）、8K 705.73/704.32（+0.20%%）、**16K 730.20/774.74（−5.75%%，band 0.42%%）** ⇒ 回退。"
            "**16384 维持**；8K 的 704 不是 chunk 缺陷，而是 1.3 s 固定成本摊销（模型 1.3+n/785 预测 11.44 s，实测 11.30 s）。" % TS)
        l = "\t".join(c)
    out.append(l)

add = "\t".join(["B5本机缺口", "P263", "`--prefill 8192`（R93 的 chunk 复标）", "W987", "count", "1", "1", "DONE_NEG",
                 "**W987 判否（%s）**：16K 段 −5.75%%（730.2 vs 774.7，band 0.42%%），2K/8K 无差；cfg_apply 自动回退。" % TS])
io.open(P, "w", encoding="utf-8", newline="").write("\n".join(out + [add]) + "\n")
print("PROGRESS: R93→DONE，+P263")
