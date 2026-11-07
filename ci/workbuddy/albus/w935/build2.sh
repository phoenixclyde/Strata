#!/bin/bash
set -u
B=~/strata166/gfx029-build
W=~/strata166/work/r77

echo "=== A. rules.ninja 里 CXX rule 的 command ==="
python3 - "$B" <<'PY'
import sys, io, os
b = sys.argv[1]
p = os.path.join(b, "CMakeFiles", "rules.ninja")
if not os.path.exists(p):
    print("  rules.ninja 不存在:", p); raise SystemExit
txt = io.open(p, encoding="utf-8", errors="replace").read().split("\n")
want = "CXX_COMPILER__strata_kernels_unscanned_Release"
for i, l in enumerate(txt):
    if l.startswith("rule " + want):
        for j in range(i, min(i+10, len(txt))):
            if j > i and not txt[j].startswith("  "):
                break
            print("  ", txt[j][:600])
        break
else:
    print("  未找到 rule，前 20 个 rule 名：")
    print([l[5:] for l in txt if l.startswith("rule ")][:20])
PY

echo
echo "=== B. 时间戳对比（谁新） ==="
ls -l --time-style=+%s $B/build.ninja 2>/dev/null | awk '{print "  build.ninja  mtime=",$6}'
ls -l --time-style=+%s $W/CMakeLists.txt 2>/dev/null | awk '{print "  CMakeLists   mtime=",$6}'
echo "  → build.ninja 更旧就会触发重配置"

echo
echo "=== C. 把构建文件的时间戳推到现在之后（绕过重配置） ==="
find $B -maxdepth 2 -name "build.ninja" -o -maxdepth 2 -name "rules.ninja" 2>/dev/null | while read f; do
  touch -d "+1 hour" "$f" 2>/dev/null && echo "  touched $f -> $(stat -c%y "$f")"
done

echo
echo "=== D. 再试单对象 ==="
docker run --rm -v $W:/src -v $B:/out -w /out strata-gfx906:0.2.9-101 \
  bash -lc "ninja CMakeFiles/strata_kernels.dir/src/kernels/ngram.cpp.o 2>&1 | tail -12" 2>&1 | tail -14
