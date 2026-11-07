#!/bin/bash
set -u
B=~/strata166/gfx029-build

python3 - "$B" <<'PY'
import sys, io, os, re

b = sys.argv[1]
bn = io.open(os.path.join(b, "build.ninja"), encoding="utf-8", errors="replace").read().split("\n")
rules_path = os.path.join(b, "CMakeFiles", "rules.ninja")
rn = io.open(rules_path, encoding="utf-8", errors="replace").read().split("\n") if os.path.exists(rules_path) else []

# 1) 找 build strata: 行
idx = [i for i, l in enumerate(bn) if re.match(r"^build strata:", l)]
print("build strata 行号:", idx)
if not idx:
    raise SystemExit("未找到 build strata 行")
line = bn[idx[0]]
print("长度:", len(line))
print("前 300:", line[:300])

# 2) rule 名
m = re.search(r"^build strata: (\S+) ", line)
rule = m.group(1) if m else None
print("rule:", rule)

# 3) rule 的 command
cmd_tpl = None
for i, l in enumerate(rn):
    if l.startswith("rule " + str(rule)):
        for j in range(i, min(i+12, len(rn))):
            if j > i and not rn[j].startswith("  "):
                break
            if rn[j].strip().startswith("command ="):
                cmd_tpl = rn[j].split("=", 1)[1].strip()
        break
print("command 模板:", (cmd_tpl or "(未找到)")[:300])

# 4) 取 $in / $out
parts = line.split(": ", 1)[1]
# 去掉 rule 名
parts = parts.split(" ", 1)[1] if " " in parts else ""
ins, outs = [], []
if " | " in parts:
    left, right = parts.split(" | ", 1)
    # right 是隐式依赖（库）
    ins = left.split()
    implicits = right.split()
else:
    ins = parts.split()
    implicits = []

# ${in} 只包含显式输入；隐式依赖也要给链接器（库）
print("显式输入数:", len(ins))
print("隐式依赖数:", len(implicits))
print("隐式前 5:", implicits[:5])
PY
