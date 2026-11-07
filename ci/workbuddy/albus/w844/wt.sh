set +e
cd /home/albus/strata166/gfx906
echo "=== 取 v0.2.9 tag ==="
timeout 240 git fetch upstream --tags --depth=1 2>&1 | tail -3
echo "tag v0.2.9 -> $(git rev-parse --short v0.2.9 2>/dev/null)"
echo "=== 补丁件是否齐 ==="
ls -l /home/albus/strata166/patches/ 2>/dev/null | head
ls -l /home/albus/strata166/tmp/restore_cmake.py 2>/dev/null || find /home/albus/strata166 -maxdepth 3 -name "restore_cmake.py" 2>/dev/null | head -3
echo "=== 建 worktree（基于 v0.2.9） ==="
git worktree list
git worktree add -B gfx906/0.2.9-mi50 /home/albus/strata166/gfx029 v0.2.9 2>&1 | tail -3
echo "--- 新 worktree:"; git -C /home/albus/strata166/gfx029 log -1 --format='%h %s' 2>/dev/null
ls /home/albus/strata166/gfx029 | head -6
