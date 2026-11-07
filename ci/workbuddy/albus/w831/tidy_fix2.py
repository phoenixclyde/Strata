# -*- coding: utf-8 -*-
"""梳理第 3 步：把 P1-4 / P1-6 / P1-7 / P1-8 落进 W828 正文。"""
import io

P = "D:/workbuddy_space/strata_ws/deploy/W828_UPSTREAM_028_PORT.md"
s = io.open(P, encoding="utf-8").read()

REPS = [
 # P1-4 判据列不一致
 ("**8 条臂、6 个新配置、两组 ABBA**（每组 3 条 512-token 贪心，判据 `tokens/window ÷ ms/window`，不是 tok/s）。",
  "**8 条臂、6 个新配置、两组 ABBA**（每组 3 条 512-token 贪心，判据 `tokens/window ÷ ms/window`，不是 tok/s）。\n\n"
  "> **AUDIT12 注（判据口径）**：声明的是 `tokens/window ÷ ms/window`，但下表 `tok/s` 列与\"相对基线\"列其实是 **wall tok/s**。\n"
  "> 两列相差 1.2–3.7%，与要判的效应同量级。按**声明判据**复算：`ta` 1.79/39.44=**45.38**、`th` 1.79/37.50=**47.73（+5.2%）**、`tk` 1.63/35.24=**46.25（+1.9%）**。\n"
  "> 所以\"平地 / 生产在正中\"这个结论**只在 wall 口径下成立**；换判据列，`th` 反而领先。要用哪一列，必须先把两列的差说清。"),

 # P1-6 FP16 行自相矛盾（补成第 3 条）
 ("2. **固定项的来源被判定了**：数学路径一换，固定项从 1.20 s 涨到 3.06 s ⇒ 它不是 HTTP/模板开销，\n"
  "   而是**第一个 chunk 的 staging + 计算**。所以它不能靠\"减框架开销\"拿掉，只能靠更快的内核。",
  "2. **固定项的来源被判定了**：数学路径一换，固定项从 1.20 s 涨到 3.06 s ⇒ 它不是 HTTP/模板开销，\n"
  "   而是**第一个 chunk 的 staging + 计算**。所以它不能靠\"减框架开销\"拿掉，只能靠更快的内核。\n"
  "3. **AUDIT12 更正：上表 FP16 那一行自相矛盾** —— `3.06 s + 1151/463 = 5.55 s`，表里却写 6.22 s；\n"
  "   若以 6.22 s 与 12.42 s 反解，则是 `4.00 s + 518 tok/s`。两组数**不能同时引用**。\n"
  "   结论（FP16 明显更慢）不受影响，但引用这条时只能引\"固定项\"或\"边际\"其中之一。\n"
  "4. **这条结论有对照臂，但原稿漏记**：同一 harness（停生产、起容器、3 条热身、33 args/14 env）跑默认 env 得\n"
  "   **1206 ms + 1.317 ms/tok**，与活生产的 `1197 + 1.316` 吻合 ⇒ **基线不是冷启动伪影**。\n"
  "   这一臂是本节结论成立的关键，缺了它，读者无法排除\"热引擎 vs 冷容器\"的替代解释。"),

 # P1-8 口径混用
 ("（4.3K→7.2K 区间的边际是 1.69 ms/tok，比 `auto` 的 1.32 还差）",
  "（4.3K→7.2K 区间的边际是 1.69 ms/tok；**同口径**下 `auto` 在同一区间是 **1.64** —— 两者基本持平，不能说\"还差\"。\n"
  "原文拿三点拟合斜率 1.32 去比实测区间斜率，口径不一致 —— AUDIT12 P1-8）"),
]

ok = True
for old, new in REPS:
    c = s.count(old)
    print("%s hits=%d %s" % ("OK " if c == 1 else "!! ", c, old[:56].replace("\n", " ")))
    if c != 1:
        ok = False
    else:
        s = s.replace(old, new, 1)

if ok:
    io.open(P, "w", encoding="utf-8", newline="\n").write(s)
    print("written", len(s))
print("ALL_OK" if ok else "MISSING")
