set +e
cd /home/albus/strata166/gfx906 || exit 1
echo "=== 现状 ==="
git log --oneline -2
git status --porcelain | head -5
echo "=== reflog（找被 reset 掉的 commit） ==="
git reflog -6 | head -8
