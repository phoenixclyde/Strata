#!/bin/bash
set -u
B=/home/albus/strata166/build-r28
R=/home/albus/strata166/pr/strata-fork

echo "=== 1) 二进制自检（容器内跑，需要 ROCm 运行库） ==="
docker run --rm -v "$B":/b strata-gfx906:0.2.9-101 bash -lc '
  /b/strata --version 2>&1 | head -3
  echo "--- help 前 3 行 ---"
  /b/strata --help 2>&1 | head -3
'
echo "size=$(stat -c%s $B/strata)  md5=$(md5sum $B/strata | cut -c1-32)"

echo
echo "=== 2) 关键开关字面量是否在二进制里 ==="
for k in STRATA_GFX906_TUNED STRATA_PREFILL_TIMING STRATA_SELECT_SIMT STRATA_PF_GROUP_SCRATCH STRATA_PENALTY_PROMPT strata-spec; do
  printf "  %-26s %s\n" "$k" "$(strings -a $B/strata | grep -c "$k")"
done
echo "  fatal GPU (server side is python, so 0 here is expected): $(strings -a $B/strata | grep -c 'fatal GPU error')"

echo
echo "=== 3) 打 tag 并前移主线 ==="
cd "$R" || exit 1
TRIAL=$(git -C /home/albus/strata166/work/rebase-trial rev-parse HEAD)
echo "rebase tip = $TRIAL"
git tag -f mi50-0.2.10-r28 "$TRIAL" -m "gfx906/mi50 rebased onto upstream v0.2.10 (ffa80d73); engine 0.1.56; 37 local commits replayed"
# move the mainline: the worktree has it checked out, so reset it
git reset --hard "$TRIAL" 2>&1 | tail -2
echo "--- 现状 ---"
git log --oneline -1
git describe --tags --exact-match HEAD
echo "behind/ahead vs upstream: $(git rev-list --left-right --count upstream/main...HEAD)"
git status --porcelain --untracked-files=no | wc -l
