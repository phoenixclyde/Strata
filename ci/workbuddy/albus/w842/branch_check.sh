set +e
echo "=== [1] 分支 vs 构建树：sync --check ==="
bash /home/albus/strata166/tmp/sync_gfx906.sh --check 2>&1 | tail -25
echo
echo "=== [2] 分支状态 ==="
cd /home/albus/strata166/gfx906 && git rev-parse --short HEAD && git status --porcelain | head -5
echo "ahead/behind vs origin/main:"; git rev-list --left-right --count origin/main...HEAD 2>/dev/null
echo
echo "=== [3] 9ac564f(trace) 是否进了构建树/二进制 ==="
printf 'tree  W839_TRACE : %s\n' "$(grep -c -F 'STRATA_W839_TRACE' /home/albus/strata166/src028/src/program/generate.cpp)"
printf 'bin   W839_TRACE : %s\n' "$(grep -a -c -F 'W839_TRACE' /home/albus/strata166/data/bin/strata-0.1.54n3)"
printf 'tree  apply call : %s\n' "$(grep -c -F 'W839 local' /home/albus/strata166/src028/src/program/generate.cpp)"
printf 'bin   banner     : %s\n' "$(grep -a -c -F 'MI50-class' /home/albus/strata166/data/bin/strata-0.1.54n3)"
echo
echo "=== [4] 二进制 vs 构建产物 ==="
md5sum /home/albus/strata166/data/bin/strata-0.1.54n3 /home/albus/strata166/src028/build-028r/strata
ls -l --time-style=+%H:%M /home/albus/strata166/src028/build-028r/strata /home/albus/strata166/data/bin/strata-0.1.54n3
echo
echo "=== [5] SELECT_SIMT 的解析分支（是否支持 =2） ==="
cd /home/albus/strata166/gfx906
grep -rn "STRATA_SELECT_SIMT" src include | head -12
echo
echo "=== [6] --vram-reserve-mib 与 expert-cache auto 的关系 ==="
grep -rn "vram_reserve_mib\|vram-reserve-mib" src/program/generate.cpp | head -12
