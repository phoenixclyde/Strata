set +e
D=/home/albus/strata166/rocm-libs
if [ -d "$D/.git" ]; then echo "already cloned: $(du -sh $D | cut -f1)"; exit 0; fi
echo "== $(date +%H:%M:%S) sparse clone rocm-libraries（只要 hipblaslt/tensilelite）"
cd /home/albus/strata166
timeout 900 git clone --depth 1 --filter=blob:none --sparse \
  https://gh-proxy.com/https://github.com/ROCm/rocm-libraries.git "$D" 2>&1 | tail -4
cd "$D" || exit 1
timeout 600 git sparse-checkout set projects/hipblaslt/tensilelite 2>&1 | tail -3
echo "--- 结果:"
du -sh "$D" 2>/dev/null
find "$D/projects/hipblaslt/tensilelite" -maxdepth 2 -type d 2>/dev/null | head -12
echo "--- Logic 在哪:"
find "$D" -maxdepth 5 -type d -name "Logic" 2>/dev/null | head -4
echo "--- vega20 相关:"
find "$D" -maxdepth 6 -iname "*vega20*" 2>/dev/null | head -8
