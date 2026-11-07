#!/usr/bin/env python3
# W839-39 修门禁：BIN 默认取生产 exe；修 grep -c || echo 0 的双零
import io, re

P = "/home/albus/strata166/tmp/verify_patches.sh"
s = io.open(P, encoding="utf-8").read()
if "W839-39" in s:
    print("already patched"); raise SystemExit(0)

# 1) BIN 默认值：从生产配置取 exe（映射 /data -> 宿主）
old_bin = 'BIN="${2:-/home/albus/strata166/data/bin/strata-0.1.54n2}"'
assert old_bin in s, "BIN line not found"
new_bin = '''# W839-39: default the binary to whatever production actually runs, not a hard-coded name -- a gate that
# checks an old file reports OK while the running engine is missing the patch.
_cfg=/home/albus/strata166/data/strata-huihui-ud-iq4_xs.json
_dex=$(python3 -c "import json;print(json.load(open('$_cfg')).get('exe') or '')" 2>/dev/null || true)
_dex=$(printf '%s' "$_dex" | sed 's#^/data/#/home/albus/strata166/data/#')
BIN="${2:-${_dex:-/home/albus/strata166/data/bin/strata-0.1.54n3}}"'''
s = s.replace(old_bin, new_bin)

# 2) grep -c ... || echo 0  ->  || true   （会输出两个 0，导致 integer expression expected）
n_before = s.count("|| echo 0)")
s = s.replace("|| echo 0)", "|| true)")
print("replaced %d '|| echo 0)'" % n_before)

io.open(P, "w", encoding="utf-8", newline="\n").write(s)
print("gate patched, size", len(s))
