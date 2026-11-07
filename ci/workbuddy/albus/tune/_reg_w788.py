# -*- coding: utf-8 -*-
"""W788：登记 P95（HC 归因基线）。"""
import io, shutil, time

REG = r"D:/workbuddy_space/strata_ws/deploy/params/PARAM_REGISTER.tsv"
shutil.copy2(REG, REG + ".bak_w788_" + time.strftime("%Y%m%d_%H%M%S"))

P95 = "\t".join([
    "P95", "REF", "HC 投影归因", "16.1%", "decode", "REFERENCE", "-", "-", "-",
    "【W788 归因 2026-10-25 05:3x，只读源码+pack索引+已有阶段计时，未改码未动生产】"
    "结构（index.txt 实读）：48 层 × 4 矩阵（hc_attn/hc_ffn 的 down+up），down=10240->320、up=320->10240，"
    "HC=4 streams、LR=320、hidden 2560；pack 里 bf16 6,553,600 B/矩阵，Q8 副本约 3.28 MB/矩阵"
    "=> 629 MB/窗口 @805 GB/s = **0.78 ms 地板**。实测（M 档 97 窗口）HC 合计 **7.42 ms**："
    "norm 0.59（其中 hc0 0.49 vs hc1 0.06 差 8 倍，未解释）、down 3.48、up 3.40 => **9.5 倍差**。"
    "根因（down）：fused_gr.cu:40-42 THREADS=256/WARPS=8/DOWN_BLOCKS=320/8=40(+1 inject)=**41 blocks**，"
    "而 MI50 有 60 CU => 19 个 CU 空转；shared = T×TILEV×4B = 3.33×2560×4 ≈ **34 KB** => 1 block/CU => 8 warps/40 = **20%**；"
    "合计 68%×20% ≈ **13.6%**，与 9.5 倍同量级。源码注释自承『smaller tiles raise how many blocks share an SM (the 41-block grid)』。"
    "根因（up）：UPM_COLS=16/UPM_BLOCKS=160，shared 仅 12 KB => 5 blocks/CU，占用是满的；但 K=320 太短，"
    "每线程仅 266 MAC => **latency bound**，与 down 不同因，不能同一改法。"
    "路径 A：TILEV 2560->1280（shared 17 KB，3 blocks/CU），判据 hc0 down >= -20%。"
    "路径 B：借 routeK dense_gemv:10-18 的 RPT/KCHUNK（N=320/RPT=4 × KSPLIT 5 = 400 blocks），需 reduce；"
    "routeK 的『K-split REJECTED』否的是 M=1 且 N 大（能填满）的 dense GEMV，不适用本形状。"
    "工具：166 与镜像均有 rocprofv3（rocprofiler-compute 3.7.0）。",
    "下一步：rocprofv3 --kernel-trace 确认 down 的 stall 归因，再决定 A 或 B"])

lines = io.open(REG, encoding="utf-8-sig").read().splitlines()
out = [ln for ln in lines if not ln.startswith("P95\t")] + [P95]
io.open(REG, "w", encoding="utf-8", newline="\n").write("\n".join(out) + "\n")
print("register updated, rows =", len(out))
