#!/bin/bash
set -u
W=~/strata166/work/r77
rm -rf "$W"
mkdir -p "$W"
rsync -a --exclude=.git ~/strata166/pr/strata-fork/ "$W"/ || exit 1
echo "tree ready: $(du -sh $W | cut -f1)"

cd "$W" || exit 1
echo
echo "=== 生成 e1b27d54 补丁 ==="
cd ~/strata166/pr/strata-fork
git format-patch -1 e1b27d54 --stdout > /tmp/e1b27d54.patch 2>/dev/null
wc -l /tmp/e1b27d54.patch

echo
echo "=== 先上 5a13c34f（生产已在用） ==="
git format-patch -1 5a13c34f --stdout > /tmp/5a13c34f.patch 2>/dev/null
cd "$W" || exit 1
git init -q . 2>/dev/null
git apply --check /tmp/5a13c34f.patch 2>&1 && echo "5a13c34f: OK (no conflict)" || echo "5a13c34f: CONFLICT"
git apply /tmp/5a13c34f.patch 2>&1 && echo "5a13c34f applied"

echo
echo "=== 试打 e1b27d54 ==="
git apply --check --verbose /tmp/e1b27d54.patch 2>&1 | tail -20
echo "RC=$?"

echo
echo "=== server.py 的前置符号是否都在 ==="
grep -c "class EngineDied" serve/server.py
grep -c "_raise_if_fatal_gpu" serve/server.py
grep -c "^import time\|^import time$" serve/server.py
grep -n "self.last_err" serve/server.py | head -3
grep -n "self.ended" serve/server.py | head -3
