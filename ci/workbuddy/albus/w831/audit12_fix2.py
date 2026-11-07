# -*- coding: utf-8 -*-
"""AUDIT12 第二轮：清掉残留在 W829 / W828 的旧数字。"""
import io

REPS = {
 "W829_OPT_PLAN.md": [
  ("上游给 gfx1151 集显开的 15 项 exact 优化里，",
   "上游给 gfx1151 集显开的 **19 项** exact 优化里（原文写 15 项，AUDIT12 按 `arch_defaults.cpp:58-90` 逐条数得），"),
  ("    每窗口读 ~3.9 GB ⇒ 实测 **~375–400 GB/s**（MI50 峰值 37–40%）。换 UD-Q3_K_XL 约 **+6% decode**，",
   "    每窗口读 **~3.2 GB**（21.4/层 × **48 层** × 3.1 MB）⇒ 实测 **~300 GB/s**（MI50 峰值 ~30%）。换 UD-Q3_K_XL 约 **+6% decode**，\n"
   "    （AUDIT12 更正：原文按 60 层算成 3.9 GB / 375–400 GB/s / 37–40%；模型实为 48 层，见 P206。+6% 不受影响，它走的是 23.4%×25%）"),
  ("机理部分仍成立（`=0` 的固定项 4.74 s ≈ PCIe 搬 72 GB @15 GB/s）。",
   "机理部分仍成立（`=0` 的固定项 4.74 s ≈ PCIe 搬 **52 GB** @**11 GB/s**；原文按 60 层写 72 GB/15 GB/s，AUDIT12 更正 —— 15 GB/s 已超 PCIe 3.0 x16 上限）。"),
  ("但要用它必须 `--batch ≥ 9`，而 9 slots 要 26.6 GiB。",
   "但要用它必须 `--batch ≥ 9`，而 9 slots 要 26.6 GiB（实测 8 slots 已 OOM：23.60 GiB 时只剩 156 MiB）。"),
 ],
 "W828_UPSTREAM_028_PORT.md": [
  ("`auto` 的 1.20 s 是 CPU 起跑延迟，`=0` 的 4.74 s 是 PCIe 搬运 72 GB。",
   "`auto` 的 1.20 s 是 CPU 起跑延迟，`=0` 的 4.74 s 是 PCIe 搬运约 52 GB（AUDIT12：原文 72 GB 按 60 层算）。"),
 ],
}

ok = True
for fn, reps in REPS.items():
    p = "D:/workbuddy_space/strata_ws/deploy/" + fn
    s = io.open(p, encoding="utf-8").read()
    for old, new in reps:
        c = s.count(old)
        print("%s hits=%d %s" % ("OK " if c == 1 else "!! ", c, old[:60]))
        if c != 1:
            ok = False
        else:
            s = s.replace(old, new, 1)
    if ok:
        io.open(p, "w", encoding="utf-8", newline="\n").write(s)
        print("  written", fn, len(s))
print("ALL_OK" if ok else "MISSING")
