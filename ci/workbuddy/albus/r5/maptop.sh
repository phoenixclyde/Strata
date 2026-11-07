#!/bin/bash
# 引擎进程按文件聚合的常驻页（Rss），MB 降序。用法：maptop.sh [pid]
p=${1:-$(pgrep -f "build-906/strata --serve" | head -1)}
echo "pid=$p"
awk '
/^[0-9a-f]+-[0-9a-f]+ / { name = $6 }
/^Rss:/ { if (name != "") s[name] += $2 }
END { for (k in s) printf "%10.1f MB  %s\n", s[k]/1024, k }
' /proc/$p/smaps | sort -rn | head -10
echo "--- rollup"
grep -E "^(Rss|Pss|Anonymous|Shared_File|Private_File|Pss_Anon|Pss_File):" /proc/$p/smaps_rollup
