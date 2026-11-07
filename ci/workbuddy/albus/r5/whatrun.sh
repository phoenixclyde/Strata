#!/bin/bash
# 当前这次启动到底开了什么（严格按最后一次 engine started 往后看）
L=/home/albus/strata166/data/strata-huihui-ud-iq4_xs.log
N=$(grep -a -n "engine started" "$L" | tail -1 | cut -d: -f1)
echo "last engine started at line $N:"
sed -n "${N}p" "$L" | cut -c1-200
echo "--- 本次启动里的 MTP / ngram / PLE 证据"
tail -n +$N "$L" | grep -a -E "mtp: |draft layer|draft head|PLE on, table|PLE direct read probe|suffix drafts|route tail skip|on the CPU" | cut -c1-150
echo "--- 进程实况（容器内）"
p=$(pgrep -f "build-906/strata --serve" | head -1)
echo "pid=$p"
tr "\0" "\n" < /proc/$p/environ 2>/dev/null | grep -E "^STRATA_" | sort | sed 's/^/  /'
tr "\0" "\n" < /proc/$p/cmdline 2>/dev/null | grep -E "^--(mtp|mtp-window|spec|spec-min-p|prefill|ple)" | sed 's/^/  ARG /'
