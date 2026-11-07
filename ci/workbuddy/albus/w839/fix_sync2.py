#!/usr/bin/env python3
# W839-35b 修复 3b 段：替换到「(--check: nothing written)」之前的那段
import io

P = "D:/workbuddy_space/strata_ws/albus/w836/sync_gfx906.sh"
s = io.open(P, encoding="utf-8").read()

start = s.find('say "=== 3b.')
tail_marker = 'if [ "$CHECK" -eq 1 ]; then\n  say "(--check: nothing written)"'
end = s.find(tail_marker)
print("start", start, "end", end)
if start < 0 or end < 0 or end <= start:
    print("abort"); raise SystemExit(2)

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
drift=$((drift+pdrift))

'''

s2 = s[:start] + GOOD + s[end:]
io.open(P, "w", encoding="utf-8", newline="\n").write(s2)
print("repaired %d -> %d" % (len(s), len(s2)))
