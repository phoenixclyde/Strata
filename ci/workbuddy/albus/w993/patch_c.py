import io, time
TS = time.strftime("%Y-%m-%d %H:%M")
P = "D:/workbuddy_space/strata_ws/deploy/PROGRESS.tsv"
lines = io.open(P, encoding="utf-8").read().splitlines()
out = []
for l in lines:
    c = l.split("\t")
    if len(c) > 8 and c[1] == "R95":
        c[8] = (c[8] or "") + (
            " 【W993 候选 C 定界 %s】`kPfDequant` 实为**专家权重聚拢/重排进 MMQ group buffer**（prefill.cpp:5543/5588/7005），"
            "不是纯反量化。现成免 gather 的开关是 `STRATA_MMQ_DIRECT=1`（docs/DETAILS.md §1511：170/1217 tok 的 read-in −18~24%%、"
            "greedy token 一致），但需要构建 `-DSTRATA_MMQ_TAB=ON` —— **我们 build-r32 只有 KQUANTS/TQ/TQP，无 TAB**；"
            "且文档明说多数专家从 RAM 流式时收益 <1.5%%，我们 VRAM 仅 21.79 GiB 正是该情形 ⇒ **暂不重编**。"
            "R86 的 `kq_bench` 只有 r28 有且该构建 `mmq::built()=false` ⇒ 需按 r32 重编一次才能取新数。" % TS)
        l = "\t".join(c)
    out.append(l)
io.open(P, "w", encoding="utf-8", newline="").write("\n".join(out) + "\n")
print("PROGRESS: R95 补 C 定界")
