#!/bin/bash
set -u
B=~/strata166/gfx029-build

echo "=== build.ninja 里 ngram 相关行 ==="
grep -n "ngram" $B/build.ninja 2>/dev/null | head -14 | cut -c1-220

echo
echo "=== compile_commands.json 里的 ngram ==="
python3 - "$B" <<'PY'
import json, sys, os
b = sys.argv[1]
p = os.path.join(b, "compile_commands.json")
d = json.load(open(p))
hit = [e for e in d if "ngram" in e["file"]]
print("总条目 %d，ngram 命中 %d" % (len(d), len(hit)))
for e in hit:
    print("file:", e["file"])
    print("dir :", e["directory"])
    c = e.get("command") or " ".join(e.get("arguments", []))
    print("cmd :", c[:700])
PY
