# -*- coding: utf-8 -*-
"""补回 R5-A（STRATA_GR_TILEV）实验留档：P96 作为 REFERENCE，记录未完成状态与镜像位置。"""
import io, shutil, time

REG = r"D:/workbuddy_space/strata_ws/deploy/params/PARAM_REGISTER.tsv"
shutil.copy2(REG, REG + ".bak_p96_" + time.strftime("%Y%m%d_%H%M%S"))

P96 = "\t".join([
    "P96", "ENV", "STRATA_GR_TILEV", "未定", "decode", "PENDING", "-", "-", "-",
    "【W788 R5-A 2026-10-25 05:4x-06:0x，实验未完成】动机：HC down 实测 7.42 ms/窗口 vs 0.79 ms 权重地板（9.5 倍），"
    "根因是 fused_gr.cu 的 DOWN_BLOCKS=41 blocks（60 CU，19 个空转）+ shared 34 KB => 1 block/SM => 约 13.6% 占用。"
    "实现：把 `down_chunk()` 里 gfx906 硬编码的 `small_tile=false` 改成 env 门控（不设=2560，与 0.2.4 逐字节相同；"
    "=1280 走小 tile，shared 17 KB => 3 blocks/SM）。1280 的实例化与 `tv==1280` 分支本来就在代码里（:1307-1310）。"
    "已完成：镜像 strata-gfx906:0.2.4r5（二进制 34,771,968 B，md5 0a77b236c78de832，含断言 7 项）；"
    "臂 A（tilev=2560，3 runs，98/100/95 窗口）decode timing = 62.72（预热）/ 53.17 / 53.02 ms/窗口。"
    "**未完成：臂 B（tilev=1280）从未运行** => 无任何效果结论。"
    "教训：本次在 A/B 未跑完时就把 0.2.4r5 切到了生产，属流程违规（纪律⑧），已回滚到 0.2.4。",
    "待办：在临时容器(8091)上跑完两臂再谈切换；镜像与容器 strata166-407.r5 留档勿用"])

lines = io.open(REG, encoding="utf-8-sig").read().splitlines()
out = [ln for ln in lines if not ln.startswith("P96\t")] + [P96]
io.open(REG, "w", encoding="utf-8", newline="\n").write("\n".join(out) + "\n")
print("P96 restored, rows =", len(out))
