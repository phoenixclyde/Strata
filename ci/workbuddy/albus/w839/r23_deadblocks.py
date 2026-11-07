#!/usr/bin/env python3
# W839-23 静态清点：generate.cpp 里被 STRATA_USE_HIP 门控、而 gfx906 构建拿不到的块
import io, re

P = "/home/albus/strata166/src028/src/program/generate.cpp"
lines = io.open(P, encoding="utf-8", errors="replace").read().split("\n")

blocks = []
depth = 0
for i, l in enumerate(lines):
    if re.match(r"\s*#\s*if", l):
        depth += 1
    if "defined(STRATA_USE_HIP)" in l and l.strip().startswith("#if"):
        # 找本块的注释与首条语句
        nxt = []
        for j in range(i + 1, min(i + 4, len(lines))):
            t = lines[j].strip()
            if t:
                nxt.append(t[:110])
        blocks.append((i + 1, l.strip()[:80], nxt))

print("generate.cpp 中 #if defined(STRATA_USE_HIP) 的块：%d" % len(blocks))
gfx906_only = [b for b in blocks if "STRATA_HIP_GFX906" not in b[1]]
print("其中不含 STRATA_HIP_GFX906 的（gfx906 构建拿不到）：%d" % len(gfx906_only))
print()
for n, (ln, cond, nxt) in enumerate(gfx906_only, 1):
    print("%2d) line %5d  %s" % (n, ln, cond))
    for t in nxt:
        print("        ", t)

# 再看反向：哪些块已经兼容 gfx906
both = [b for b in blocks if "STRATA_HIP_GFX906" in b[1]]
print()
print("已兼容 gfx906 的块：%d" % len(both))
for ln, cond, nxt in both:
    print("   line %5d  %s" % (ln, cond))
