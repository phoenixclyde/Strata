#!/usr/bin/env python3
# W839-42 修 W836 的更正横幅（上一版反引号被 shell 执行）
import io

P = "D:/workbuddy_space/strata_ws/deploy/W836_BRANCH.md"
s = io.open(P, encoding="utf-8").read()
start = s.find("> **W839 更正（2026-10-31）**")
end = s.find("## 10 第 8 个 commit")
if start < 0 or end < 0 or end <= start:
    print("abort", start, end); raise SystemExit(2)

NOTE = (
"> **W839 更正（2026-10-31）**：本节写的「入口」当时只是**加了一张表**，表本身没有被任何编译单元引用 ——\n"
"> apply_arch_defaults 的调用点在 `#if defined(STRATA_USE_HIP)` 块内，而 gfx906 构建只定义 STRATA_HIP_GFX906，\n"
"> 于是 arch_defaults.cpp 被链接器整块丢掉（nm 无符号、二进制无横幅字符串）。本节「重编后行为应不变」\n"
"> 因此是对的，但理由不完整：**不变是因为表根本没跑**。调用点由 W839 补上（commit 1309b1d，trace 为 9ac564f），\n"
"> 详见 W839_ARCH_ENTRY.md。\n\n"
)
s2 = s[:start] + NOTE + s[end:]
io.open(P, "w", encoding="utf-8", newline="\n").write(s2)
print("repaired", len(s), "->", len(s2))
print(s2[start:start+520])
