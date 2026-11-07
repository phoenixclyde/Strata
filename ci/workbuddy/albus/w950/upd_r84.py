# -*- coding: utf-8 -*-
import io
P = "D:/workbuddy_space/strata_ws/deploy/PROGRESS.tsv"
ADD = (" 【W950 定位 2026-11-04 16:0x｜A 级】最小复现 `~/strata166/w950/probe1.cu`（1 block_q4_K、1 行、K=256、1 线程、串行）："
       "**kernel y = -702.4599，host ref = -7.0246，ratio = 99.9999** —— 差恰好 100 倍，原因是我 host 参考里多乘了激活量化 scale 0.01，"
       "**kernel 的 Q4_K 公式本身是对的**（d/dmin 读出来 0.012299/0.004559 与 host 一致，sumi=1446、sa=-237 也可复算）。"
       "⇒ dot8 的数学与 Q4_K 解析已排除；**M=64 版（q4k_gemm_dot8.cu）的 rel_l2≈0.995 是那一版特有的实现 bug**（多 warp/token 索引或 scale 数组索引），"
       "下一步在 M=64 版里逐项对齐 probe1 的写法后再判吞吐。")

with io.open(P, encoding="utf-8", newline="") as f:
    lines = f.read().split("\n")
out = []
for ln in lines:
    if "\t" in ln:
        f8 = ln.split("\t")
        if len(f8) >= 9 and f8[1] == "R84":
            f8[8] += ADD; ln = "\t".join(f8)
    out.append(ln)
with io.open(P, "w", encoding="utf-8", newline="") as f:
    f.write("\n".join(out))
print("R84 +probe1")
