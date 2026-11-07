# -*- coding: utf-8 -*-
"""梳理第 2 步：把仍留在正文里的旧数字改到位，并修报告自身的计数。"""
import io

R = {
 "D:/workbuddy_space/strata_ws/deploy/W828_UPSTREAM_028_PORT.md": [
  ("| QSA 层主体（q+q-idx 1.67 + attention 1.78 + scores+topk 0.89 + out-proj 0.60 + kv 0.83） | 5.88 | 13.1% |",
   "| QSA 层主体（q+q-idx 1.67 + attention 1.78 + scores+topk 0.89 + out-proj 0.60 + kv 0.83） | 5.88（子项和 **5.77**，余 0.11 未归类 —— AUDIT12 P2-5） | 13.1% |"),
  ("**缓存命中对照**：同一个 7123-token prompt 再发一次只要 **0.296 s**（≈27k tok/s）",
   "**缓存命中对照**：同一个 7123-token prompt 再发一次只要 **0.296 s**（≈**24k** tok/s；原文写 27k，AUDIT12 复算 7123/0.296=24.1k）"),
  ("在 prefill 上，数学路径的选择是**数量级**的。**`STRATA_PREFILL_MMQ` 永远不要设 0**（踩一脚就是 1.8 倍慢）。",
   "在 prefill 上，数学路径的选择是**数量级**的。**`STRATA_PREFILL_MMQ` 永远不要设 0**（踩一脚慢 **1.64 倍**；原文写 1.8 倍，AUDIT12 复算 760/463）。"),
  ("**落地口径**（以后对外报数就用这一套）：新对话 500 tok ≈ **1.9 s**；3K ≈ **5.2 s**；8K ≈ **11.7 s**；",
   "**落地口径**（**AUDIT12 已按 n2 重算**：常数 915 ms + 1.316 ms/tok）：新对话 500 tok ≈ **1.6 s**；3K ≈ **4.9 s**；8K ≈ **12.2 s**\n"
   "（>4.3K 后边际会变大，纯线性外推给 11.7 s、偏低；原文 1.9/5.2/11.7 是 0.1.54n 的口径，已过期 0.28 s）；"),
  ("- 启动日志写死 `strata serve: prompt chunk auto: 8192 tokens, a 384-slot ring`，我们的 prompt（≤4.4K）**都在一个 chunk 内**",
   "- 启动日志写死 `strata serve: prompt chunk auto: 8192 tokens, a 384-slot ring`，当时测的 prompt（≤4.4K）**都在一个 chunk 内**\n"
   "  （§6.16 另外测了 7.2K 与 14.3K，后者已跨 chunk，另论 —— AUDIT12 P2-10）"),
  ("补丁门禁扩到 **13 项**（新增 W831 三条、WEB-UI 三条），当前 **13/13 PASS**。",
   "补丁门禁扩到 **13 项**（8 项 + 新增 5 项：W831 三条、WEB-UI 由 1 条扩为 3 条；原文写\"新增 6\"，AUDIT12 更正），当前 **13/13 PASS**。"),
 ],

 "D:/workbuddy_space/strata_ws/deploy/W827_UPSTREAM_028_ASSESS.md": [
  ("我们重启频繁；W826 那次 MMQ 臂启动就撞过 `memory guard: current 105.4 GiB, available 20.3 GiB`",
   "我们重启频繁；**W828 那次**（10-31）MMQ 臂启动就撞过 `memory guard: current 105.4 GiB, available 20.3 GiB`"
   "（原文写\"W826 那次\"，时序不可能 —— W827 写于 10-30 23:49，AUDIT12 P2-11）"),
 ],

 "D:/workbuddy_space/strata_ws/deploy/AUDIT12_W826_W831.md": [
  ("**P0 = 3 · P1 = 11 · P2 = 10；撤回 3 条（含子 agent 的两条、我自己的半条）。**",
   "**P0 = 3 · P1 = 11 · P2 = 12；撤回 3 条（含子 agent 的两条、我自己的半条）。**"),
 ],
}

ok = True
for p, reps in R.items():
    s = io.open(p, encoding="utf-8").read()
    for old, new in reps:
        c = s.count(old)
        print("%s hits=%d %s" % ("OK " if c == 1 else "!! ", c, old[:58]))
        if c != 1:
            ok = False
        else:
            s = s.replace(old, new, 1)
    if ok:
        io.open(p, "w", encoding="utf-8", newline="\n").write(s)
        print("  written", p.split("/")[-1], len(s))
print("ALL_OK" if ok else "MISSING")
