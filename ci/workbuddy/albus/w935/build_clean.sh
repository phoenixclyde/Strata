#!/bin/bash
set -u
B=~/strata166/gfx029-build
W=~/strata166/work/r77

python3 - "$B" > /tmp/gen2.sh <<'PY'
import sys, io, os, re

b = sys.argv[1]
bn = io.open(os.path.join(b, "build.ninja"), encoding="utf-8", errors="replace").read().split("\n")
rn = io.open(os.path.join(b, "CMakeFiles", "rules.ninja"), encoding="utf-8", errors="replace").read().split("\n")

targets = {
    "CMakeFiles/strata_prefill.dir/src/prefill/prefill.cpp.o": "/src/src/prefill/prefill.cpp",
    "CMakeFiles/strata.dir/src/program/generate.cpp.o": "/src/src/program/generate.cpp",
}

print("#!/bin/bash")
print("set -e")
print("cd /out")

for out, src in targets.items():
    idx = [i for i, l in enumerate(bn) if l.startswith("build " + out + ":")]
    if not idx:
        print("echo 'NOT FOUND: %s'" % out)
        continue
    i = idx[0]
    line = bn[i]
    rule = line.split(": ", 1)[1].split(" ", 1)[0]
    # 变量
    vars = {}
    j = i + 1
    while j < len(bn) and bn[j].startswith("  "):
        s = bn[j].strip()
        if " = " in s:
            k, v = s.split(" = ", 1)
            vars[k] = v
        j += 1
    # rule command
    tpl = None
    for k, l in enumerate(rn):
        if l.startswith("rule " + rule):
            for m in range(k, min(k+14, len(rn))):
                if m > k and not rn[m].startswith("  "):
                    break
                if rn[m].strip().startswith("command ="):
                    tpl = rn[m].split("=", 1)[1].strip()
            break
    if not tpl:
        print("echo 'NO RULE for %s'" % out)
        continue
    cmd = tpl
    cmd = cmd.replace("${LAUNCHER}", "").replace("${CODE_CHECK}", "")
    cmd = cmd.replace("$in", src).replace("$out", out)
    for k in ("DEFINES", "INCLUDES", "FLAGS"):   # 只展开这三个；其余留给 -MD 等
        cmd = cmd.replace("$" + k, vars.get(k, ""))
    cmd = cmd.replace("$DEP_FILE", out + ".d")
    cmd = re.sub(r"\s+", " ", cmd)
    print("echo '=== compiling %s ==='" % out)
    print(cmd)
PY

echo "=== 生成的编译脚本（前 3 行 + 行数） ==="
head -3 /tmp/gen2.sh
wc -l /tmp/gen2.sh
echo "--- 每条命令的前 200 字符 ---"
grep -E "clang\+\+|hipcc" /tmp/gen2.sh | cut -c1-200

echo
echo "=== 执行（约 6-10 分钟） ==="
docker run --rm -v $W:/src -v $B:/out -v /tmp/gen2.sh:/tmp/gen2.sh -w /out strata-gfx906:0.2.9-101 \
  bash /tmp/gen2.sh 2>&1 | tail -20
