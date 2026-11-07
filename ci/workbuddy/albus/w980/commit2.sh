#!/bin/bash
cd /home/albus/strata166/pr/strata-fork
echo "== borrows 行 =="
docker exec strata166-407 grep -a "borrows" /data/strata-huihui-ud-iq4_xs.log | tail -2
echo
echo "== gitignore 里有没有 ci/state =="
grep -n "state" .gitignore 2>/dev/null || echo "(no)"
echo
echo "== 提交 cfg_apply 探针修正 =="
git add ci/cfg_apply.py
git -c user.name=strata -c user.email=strata@local commit -q -m "cfg_apply: measure with unique prompts (a repeated prompt is a prefix hit, not a measurement)

The first version measured TTFT with one fixed 2K prompt, so every sample after the first was
a prefix hit: 0.29 s instead of ~3.9 s.  Each sample now carries a random tag, and decode is
measured in-process (64 tokens, n samples, median + CV) instead of parsing bench.py's path." 2>&1 | tail -3
git log -1 --format=' %h %s' | cut -c1-55
printf ' dirty=%s\n' "$(git status --porcelain | wc -l)"
