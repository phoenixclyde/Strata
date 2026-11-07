set +e
cd /home/albus/strata166/gfx906 || exit 1
git reset --hard cc8a071 2>&1 | tail -2
git log --oneline -2
echo "=== 重打补丁是否还在 ==="
grep -c -F "W842 local" src/kernels/cuda/qsa_select.cu
echo
echo "=== push 到 origin（phoenixclyde/Strata） ==="
timeout 120 git push origin gfx906/0.2.8-mi50 2>&1 | tail -6
echo "push rc=$?"
echo
echo "=== 远端是否已有该 commit ==="
git fetch origin gfx906/0.2.8-mi50 2>&1 | tail -2
git rev-parse --short origin/gfx906/0.2.8-mi50 2>/dev/null
git rev-list --left-right --count origin/gfx906/0.2.8-mi50...HEAD 2>/dev/null
