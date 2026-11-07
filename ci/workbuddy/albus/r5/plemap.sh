#!/bin/bash
# 容器内运行：PLE 分片（00002-of-00003）在引擎进程里的常驻页 + 宿主页缓存概况
p=$(pgrep -f "build-906/strata --serve" | head -1)
[ -z "$p" ] && { echo "PLEMAP no-engine"; exit 0; }
awk -v pat="00002-of-00003" '
/^[0-9a-f]+-[0-9a-f]+ / { inm = (index($6, pat) > 0); next }
/^Rss:/ { if (inm) s += $2; next }
END { printf "PLEMAP rss=%.1f MB\n", s / 1024 }
' /proc/$p/smaps
grep -E "^(Cached|MemFree|MemAvailable|AnonPages):" /proc/meminfo | tr '\n' ' '
echo
