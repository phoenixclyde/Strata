#!/bin/bash
# 引擎内存分层的真实构成：anon vs file-backed、映射了哪些文件
PID=$(pgrep -f 'strata-0.1.56-090' | head -1)
echo "host pid=$PID"
echo "== smaps_rollup =="
sudo awk '/^(Rss|Pss|Shared_Clean|Shared_Dirty|Private_Clean|Private_Dirty|Anonymous|Swap|Locked):/{printf "%-16s %8.2f GiB\n", $1, $2/1048576}' /proc/$PID/smaps_rollup
echo
echo "== 前 6 个映射文件（按大小）=="
sudo awk '/^[0-9a-f]+-[0-9a-f]+ .* [0-9]+:[0-9]+ [0-9]+ +[^ ]+$/{split($1,a,"-"); sz=("0x" a[2])-("0x" a[1]); print sz, $6}' /proc/$PID/maps \
 | sort -rn | head -8 | awk '{printf "%8.2f GiB  %s\n", $1/1073741824, $2}'
echo
echo "== 匿名映射总量 =="
sudo awk '/^[0-9a-f]+-[0-9a-f]+ .* 00:00 0 +\[?/{split($1,a,"-"); s+=("0x" a[2])-("0x" a[1])} END{printf "%8.2f GiB\n", s/1073741824}' /proc/$PID/maps
