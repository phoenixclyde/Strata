#!/bin/bash
# W863 · 老分支的改动到底在不在主线里：取每条新增的代表性代码行，回主线里 grep
set -u
R=/home/albus/strata166/pr/strata-fork
cd "$R" || exit 1
for b in amd-monitor-name-consistency amd-monitor-pcie-link gfx906-build-fixes-402 \
         gfx906-cpu-share-guard web-sparkline-axis-floor gfx906/0.2.8-mi50 \
         gfx906/hipblaslt-vega20 gfx906/mmq-plan-banner gfx906/routed-stream; do
  echo "################ $b ($(git rev-parse --short "origin/$b")) ################"
  echo "--- files it touched (tip commit) ---"
  git show --stat --format='  %s' "origin/$b" 2>/dev/null | sed -n '2,8p'
  echo "--- sample added lines, and whether the main line has them ---"
  git show --format= --unified=0 "origin/$b" 2>/dev/null | grep '^+' | grep -v '^+++' \
    | sed 's/^+//' | awk 'length($0) > 28' | head -4 > /tmp/_w863_lines.txt
  while IFS= read -r ln; do
    [ -z "$ln" ] && continue
    key=$(printf '%s' "$ln" | sed 's/^[[:space:]]*//' | cut -c1-40)
    if git grep -qF -- "$key" HEAD -- . 2>/dev/null; then st="PRESENT"; else st="absent "; fi
    printf "    %s  %s\n" "$st" "$(printf '%s' "$key" | cut -c1-58)"
  done < /tmp/_w863_lines.txt
  echo
done
