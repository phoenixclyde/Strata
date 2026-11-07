#!/bin/bash
set -u
B=~/strata166/gfx029-build

echo "=== A. ninja 版本与 -t 列表 ==="
ninja --version 2>/dev/null
ninja -C $B -t list 2>&1 | head -12

echo
echo "=== B. 试 compdb ==="
ninja -C $B -t compdb 2>/dev/null | wc -c
ninja -C $B -t compdb 2>/dev/null | head -c 200

echo
echo
echo "=== C. 直接解析 build.ninja 找 ngram 的 rule 与变量 ==="
python3 - "$B" <<'PY'
import sys, re, io
b = sys.argv[1]
txt = io.open(b + "/build.ninja", encoding="utf-8", errors="replace").read()
lines = txt.split("\n")

# 找 build 行
idx = [i for i, l in enumerate(lines) if l.startswith("build CMakeFiles/strata_kernels.dir/src/kernels/ngram.cpp.o:")]
print("build 行号:", idx)
if idx:
    i = idx[0]
    print("BUILD:", lines[i][:300])
    # 后续缩进变量
    for j in range(i+1, min(i+12, len(lines))):
        if lines[j].startswith("  "):
            print("  VAR:", lines[j][:300])
        else:
            break
    # rule 名
    m = re.search(r": (\S+) ", lines[i])
    rule = m.group(1) if m else None
    print("RULE:", rule)
    # rule 定义
    ri = [k for k, l in enumerate(lines) if l.startswith("rule " + str(rule))]
    print("rule 行号:", ri)
    if ri:
        k = ri[0]
        for j in range(k, min(k+12, len(lines))):
            if j > k and not lines[j].startswith("  "):
                break
            print("  DEF:", lines[j][:400])
PY
