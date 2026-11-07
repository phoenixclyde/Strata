set +e
D=/home/albus/strata166/rocm-libs
cd "$D" || exit 1
echo "== 修 sparse checkout（clone 后文件数 0）"
git config core.sparseCheckout true
git sparse-checkout reapply 2>&1 | tail -3
echo "--- 重试 checkout:"
git checkout HEAD -- . 2>&1 | tail -3
echo "--- 结果:"
echo "  文件数: $(find . -type f -not -path './.git/*' | wc -l)"
du -sh . 2>/dev/null
ls projects/hipblaslt/tensilelite 2>/dev/null | head -10
echo "--- 关键文件:"
ls -l projects/hipblaslt/tensilelite/cmake/tensilelite_supported_architectures.cmake 2>/dev/null
ls -l projects/hipblaslt/tensilelite/tensilelite/Common/Architectures.py 2>/dev/null
