# -*- coding: utf-8 -*-
"""[W863] R27 (parallelism) is disproved by data we already had; replace it with R28 (access width).

Evidence, shape 2560->10240 at ncols=2, from the R-table sweep (sweep_cols.txt / sweep_r24.txt),
block count is inversely proportional to rows-per-block:

    rows=1   69.3 us   (most blocks)
    rows=2   62.3 us
    rows=4   59.5 us   (fewest blocks)  <- fastest
    rows=0   66.2 us   (plain kernel)

More blocks is SLOWER here, so "raise occupancy from 37% to 73%" cannot be the fix.

What the source points at instead: gr_down_q8_kernel loads the Q8_0 weights with
    q8_ld16(blk + 2 + 4*sub) | q8_ld16(blk + 4 + 4*sub) << 16
i.e. 2-byte scalar loads strided by 4 bytes -- each 32-byte sector is half used -- while the
native_mmvq wave kernel reads uint4 (16 bytes).  That is R28.
"""
import csv
import io
import shutil
import time

P = r"D:\workbuddy_space\strata_ws\deploy\PROGRESS.tsv"
shutil.copy2(P, P + ".bak_w863_%s" % time.strftime("%H%M%S"))

with open(P, encoding="utf-8") as f:
    lines = f.readlines()
head = [l for l in lines if l.startswith("#") or not l.strip()]
body = [l for l in lines if not l.startswith("#") and l.strip()]
hdr = body[0].rstrip("\n").split("\t")
rows = [dict(r) for r in csv.DictReader([b.rstrip("\n") for b in body], delimiter="\t")]

for r in rows:
    if r["id"] == "R27":
        r["status"] = "DONE_NEG"
        r["done"] = r["count"]
        r["note"] = ("**证伪（W863，用已有 R 表数据）**：同形状 2560->10240、ncols=2，block 数随 rows 反比——"
                     "rows=1 **69.3 us** / rows=2 62.3 / rows=4 **59.5**（rows=0 普通内核 66.2）。"
                     "**block 越少越快**，所以「占用率 37%→73%」不是收益方向。占用率不是瓶颈，"
                     "真正嫌疑见 R28（访存粒度）。")
        print("R27 -> DONE_NEG")

if not any(r["id"] == "R28" for r in rows):
    rows.append({
        "block": "B1参数轴",
        "id": "R28",
        "item": "HC down 内核用 2 字节标量 load 读 Q8_0 权重（q8_ld16），半个 sector 被浪费",
        "source": "W863 源码（fused_gr.cu:1795-1800）+ R27 证伪",
        "kind": "count",
        "count": "1",
        "done": "0",
        "status": "OPEN",
        "note": "`q8_ld16(blk+2+4*sub) | q8_ld16(blk+4+4*sub)<<16`：每线程两次 2 字节读、步长 4 字节，"
                "一个 32B sector 只用一半；对照 native_mmvq wave kernel 用 uint4(16B)。"
                "改法：先 uint4 读整个 Q8_0 block 到寄存器再取位，**只改读取方式、不改求和顺序** ⇒ 逐位等价，"
                "过 diff=0 即可。先用秒级小 TU 复现「2B vs 16B 读」的带宽差再重编。",
        "ref": "",
    })
    print("R28 added (OPEN)")

out = io.StringIO()
for l in head:
    out.write(l)
out.write("\t".join(hdr) + "\n")
for r in rows:
    out.write("\t".join(str(r.get(c, "")) for c in hdr) + "\n")
with open(P, "w", encoding="utf-8", newline="\n") as f:
    f.write(out.getvalue())
print("written: %d data rows" % len(rows))
