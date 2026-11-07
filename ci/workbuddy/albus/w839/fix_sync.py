#!/usr/bin/env python3
# W839-35 修复 sync_gfx906.sh 的 3b 段（上一版被 shell 展开写坏）
import io, re

P = "D:/workbuddy_space/strata_ws/albus/w836/sync_gfx906.sh"
s = io.open(P, encoding="utf-8").read()

start = s.find('say "=== 3b.')
end_marker = "drift=$((drift+pdrift))"
end = s.find(end_marker)
if start < 0:
    print("no 3b block; abort")
    raise SystemExit(2)
if end < 0:
    print("no end marker; abort")
    raise SystemExit(2)
end += len(end_marker)

GOOD = '''say "=== 3b. anchor patchers (files whose upstream copy differs between the two bases) ==="
# Those files cannot be copied: the branch holds upstream main's copy, the build tree holds v0.2.8's, and
# copying would put main's engine into a v0.2.8 build.  They are patched by an anchor script instead.
pdrift=0
for spec in $PATCHERS; do
  f=${spec#*:}
  p=$PATCHDIR/${spec%%:*}
  if [ "$CHECK" -eq 1 ]; then
    n=$(grep -c -F "W839 local" "$DST/$f" 2>/dev/null || echo 0)
    [ "$n" -ge 1 ] && printf "  applied %s\\n" "$f" || { printf "  MISSING %s\\n" "$f"; pdrift=$((pdrift+1)); }
  else
    if [ ! -f "$p" ]; then printf "  patcher missing: %s\\n" "$p"; pdrift=$((pdrift+1)); continue; fi
    python3 "$p" "$DST/$f" && printf "  ok %s\\n" "$f" || { printf "  FAILED %s\\n" "$f"; pdrift=$((pdrift+1)); }
  fi
done
say "patchers with drift: $pdrift"
drift=$((drift+pdrift))'''

s2 = s[:start] + GOOD + s[end:]
io.open(P, "w", encoding="utf-8", newline="\n").write(s2)
print("repaired; %d -> %d" % (len(s), len(s2)))
print(s2[s2.find('=== 3b.')-20:s2.find('=== 3b.')+760])
