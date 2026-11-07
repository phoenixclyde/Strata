#!/bin/bash
cd ~/strata166/pr/strata-fork || exit 1

echo "=== 三条提交的改动文件与规模 ==="
for c in fbf6e1c7 5273fb66 3cc47f02; do
  echo "########## $c ##########"
  git show --stat --format="%h %ad %s" --date=short $c | head -8
done

echo
echo "=== 三条涉及的 env 名与默认值 ==="
for e in STRATA_PF_GROUP_SCRATCH STRATA_PREFILL_ROUTED_STREAM STRATA_PF_HC_REGION; do
  echo "--- $e ---"
  git show fbf6e1c7 5273fb66 3cc47f02 2>/dev/null | grep -nE "getenv\(\"$e\"|$e" | head -4
done

echo
echo "=== 现有构建目录 ==="
ls -d ~/strata166/*build* 2>/dev/null | head -8
for d in ~/strata166/gfx029-build ~/strata166/src028/build-028r; do
  [ -f "$d/build.ninja" ] && echo "HAS build.ninja: $d"
done
