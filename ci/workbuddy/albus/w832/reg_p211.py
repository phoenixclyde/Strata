# -*- coding: utf-8 -*-
import io

REG = "D:/workbuddy_space/strata_ws/deploy/params/PARAM_REGISTER.tsv"
s = io.open(REG, encoding="utf-8").read()
row = ("P211", "MEASUREMENT", "0.1.53 vs 0.1.54n2 同源 A/B：速度无差异",
       "保持 0.1.54n2，不回滚", "measurement", "CONFIRMED",
       "—", "—", "P205/P209",
       "同镜像 strata-gfx906:0.2.8p2、同 33 args / 14 env、只差 exe（两臂都含 W793）。"
       "decode 5×128 tok T=0 中位：0.1.53 50.20 vs n2 49.90（−0.6%）；read 1958/3718/6666 tok：+1.1%/+0.8%/−0.0%；"
       "槽位 7551→7463（−88，−1.17%，来自 #4474 的 kLateAllocMib=256）。"
       "⇒ 升级在速度上 0 收益 0 回归（这次同源，原 W828 §6.1 的说法不成立，见 AUDIT12 P0-1）；"
       "88 槽位的代价没换来 decode 变慢 ⇒ 净收益为正。附带：0.1.53 可在 0.2.8p2 Python 层上正常运行（240 s 就绪），"
       "以后引擎级 A/B 只改 exe 即可。",
       "不落任何改动；结论是保持现状。")
if ("\n" + row[0] + "\t") in ("\n" + s):
    print("exists")
else:
    s += "\t".join(row) + "\n"
    io.open(REG, "w", encoding="utf-8", newline="\n").write(s)
    print("P211 added; rows", len([l for l in s.split("\n") if l.strip()]))
