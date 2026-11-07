set +e
D=/home/albus/strata166/rocm-libs
echo "===== [1] rocm-libs clone 状态 ====="
if [ -d "$D" ]; then
  du -sh "$D" 2>/dev/null
  cd "$D" && git log -1 --format='  head=%h %s' 2>/dev/null
  echo "  sparse 规则:"; git sparse-checkout list 2>/dev/null | sed 's/^/    /'
  echo "  文件数: $(find . -type f -not -path './.git/*' | wc -l)"
  ls projects/hipblaslt/tensilelite 2>/dev/null | head -8
else
  echo "  不存在"
fi
echo
echo "===== [2] gfx029 分支状态 ====="
git -C /home/albus/strata166/gfx029 rev-parse --abbrev-ref HEAD
git -C /home/albus/strata166/gfx029 status --porcelain | head -3
git -C /home/albus/strata166/gfx029 branch -a | head -8
