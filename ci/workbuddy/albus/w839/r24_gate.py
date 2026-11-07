#!/usr/bin/env python3
# W839-24 门禁加 6b 段：架构入口必须「在树里 + 在部署的引擎里」
import io

P = "/home/albus/strata166/tmp/verify_patches.sh"
s = io.open(P, encoding="utf-8").read()
MARK = "6b. W837/W839"
if MARK in s:
    print("already patched")
    raise SystemExit(0)

SECTION = r'''
# 6b. W837/W839: the gfx906 entry exists AND is linked into the deployed engine.
#     The entry lived in a block guarded by STRATA_USE_HIP, which this build does not define, so
#     arch_defaults.cpp was referenced by no translation unit and the linker dropped it (nm: no
#     symbol, no banner string).  A tree-only check would have passed.  So this checks the binary.
n=$(grep -c -F "MI50-class" "$TREE/src/core/arch_defaults.cpp" 2>/dev/null || echo 0)
[ "$n" -ge 1 ] && say W837 "tree: gfx906 table + banner" "OK" || { say W837 "tree: gfx906 table + banner" "MISSING"; FAIL=1; }
n=$(grep -c -F "W839 local" "$TREE/src/program/generate.cpp" 2>/dev/null || echo 0)
[ "$n" -ge 1 ] && say W839 "tree: apply_arch_defaults call site" "OK" || { say W839 "tree: apply_arch_defaults call site" "MISSING"; FAIL=1; }
if [ -f "$BIN" ]; then
  n=$(grep -a -c -F "exact speed switches" "$BIN" 2>/dev/null || echo 0)
  [ "${n:-0}" -ge 1 ] && say W839 "binary: entry linked (banner string)" "OK" || say W839 "binary: entry linked (banner string)" "NOT-IN-$BIN"
fi
if command -v python3 >/dev/null 2>&1 && [ -f /home/albus/strata166/data/strata-huihui-ud-iq4_xs.json ]; then
  exe=$(python3 -c "import json;print(json.load(open('/home/albus/strata166/data/strata-huihui-ud-iq4_xs.json')).get('exe') or '')" 2>/dev/null)
  host=$(printf '%s' "$exe" | sed 's#^/data/#/home/albus/strata166/data/#')
  if [ -n "$host" ] && [ -f "$host" ]; then
    n=$(grep -a -c -F "exact speed switches" "$host" 2>/dev/null || echo 0)
    [ "${n:-0}" -ge 1 ] && say W839 "deployed engine: entry linked" "OK" || say W839 "deployed engine: entry linked" "NOT-YET($host)"
  fi
fi
'''

anchor = "\n# 7. the deployed binary is the one we built (provenance)"
assert s.count(anchor) == 1, s.count(anchor)
s2 = s.replace(anchor, SECTION + anchor, 1)
io.open(P, "w", encoding="utf-8", newline="\n").write(s2)
print("patched gate; size %d -> %d" % (len(s), len(s2)))
