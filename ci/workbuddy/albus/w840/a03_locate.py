#!/usr/bin/env python3
# W840-03 定位待修原文（只读）
import io

TARGETS = {
 "D:/workbuddy_space/strata_ws/deploy/W832_OPT_PLAN_V2.md": [
   "33 条", "36 条", "停机", "<2%", "噪声底盘", "50.20", "7551", "0.029 -> ", "0.045",
   "GDN_HEAD/GDN_PP", "位等价", "符号翻正翻负", "抖动",
 ],
 "D:/workbuddy_space/strata_ws/deploy/W835_GFX906_PORT_FEASIBILITY.md": [
   "73%", "33 ms", "5~10", "3.9", "116.5", "26.5",
 ],
 "D:/workbuddy_space/strata_ws/deploy/W836_BRANCH.md": [
   "+216", "+94", "8 个 commit", "第 8", "find_dependency", "banner", "11 项",
 ],
 "D:/workbuddy_space/strata_ws/deploy/W839_ARCH_ENTRY.md": [
   "第 10 个", "18 项", "18 项全", "逐项一致", "12 820", "12820",
 ],
}
for p, keys in TARGETS.items():
    print("=" * 26, p.split("/")[-1])
    lines = io.open(p, encoding="utf-8").read().split("\n")
    for i, l in enumerate(lines, 1):
        if any(k in l for k in keys):
            print("%5d| %s" % (i, l[:190]))
