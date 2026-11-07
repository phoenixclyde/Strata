#!/bin/bash
set -u
B=~/strata166/gfx029-build

python3 - "$B" <<'PY'
import sys, io, os, re

b = sys.argv[1]
bn = io.open(os.path.join(b, "build.ninja"), encoding="utf-8", errors="replace").read().split("\n")
rules_path = os.path.join(b, "CMakeFiles", "rules.ninja")
rn = io.open(rules_path, encoding="utf-8", errors="replace").read().split("\n")

idx = [i for i, l in enumerate(bn) if re.match(r"^build strata:", l)][0]
line = bn[idx]

# 解析 build 行：显式输入 / 隐式依赖
body = line[len("build strata: "):]
rule, rest = body.split(" ", 1)
if " | " in rest:
    explicit, implicit = rest.split(" | ", 1)
    ins = explicit.split()
    deps = implicit.split()
else:
    ins = rest.split()
    deps = []

# 收集 build 行的变量（后续缩进行）
vars = {}
j = idx + 1
while j < len(bn) and bn[j].startswith("  "):
    s = bn[j].strip()
    if " = " in s or s.endswith(" ="):
        k, v = s.split(" = ", 1) if " = " in s else (s[:-2], "")
        vars[k] = v
    j += 1

# rule 的命令模板
tpl = None
for i, l in enumerate(rn):
    if l.startswith("rule " + rule):
        for k in range(i, min(i+14, len(rn))):
            if k > i and not rn[k].startswith("  "):
                break
            if rn[k].strip().startswith("command ="):
                tpl = rn[k].split("=", 1)[1].strip()
        break

print("=== build 行变量 ===")
for k, v in vars.items():
    print("  %-16s %s" % (k, v[:220]))

print()
print("=== 关键变量 ===")
for k in ("FLAGS", "LINK_FLAGS", "LINK_PATH", "LINK_LIBRARIES", "TARGET_FILE", "PRE_LINK", "POST_BUILD"):
    print("  %-16s %s" % (k, vars.get(k, "(缺)")[:300]))

# 展开（只做一层 + $in）
def expand(s):
    s = s.replace("$in", " ".join(ins))
    s = s.replace("$out", "strata")
    for k, v in vars.items():
        s = s.replace("$" + k, v)
    return s

cmd = expand(tpl or "")
# 去掉 PRE_LINK/POST_BUILD 噪声
cmd = cmd.replace("&& &&", "&&")
print()
print("=== 展开后命令（长度 %d） ===" % len(cmd))
print(cmd[:800])
print("...")

io.open("/tmp/link_strata.sh", "w").write("#!/bin/bash\nset -e\ncd /out\n" + cmd + "\n")
os.chmod("/tmp/link_strata.sh", 0o755)
print()
print("已写 /tmp/link_strata.sh")
PY
