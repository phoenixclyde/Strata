set +e
L=/home/albus/strata166/data/w844_build.log
B=/home/albus/strata166/gfx029-build/strata-0.1.55g
echo "=== 构建日志摘要 ==="
grep -aE "configure rc|ninja rc|Linking|ccache|^\[[0-9]+/[0-9]+\]" "$L" | tail -12
echo "--- 行数:"; wc -l < "$L"
echo
echo "=== 版本 ==="
docker run --rm -v /home/albus/strata166/gfx029-build:/out strata-gfx906:0.2.8p2 /out/strata-0.1.55g --version 2>&1 | head -5
echo
echo "=== 补丁是否在二进制里 ==="
for k in "MI50-class" "exact speed switches" "STRATA_SELECT_SIMT=2), tiles 32/128" "W839" "W842 local" "W793" "BW_REFRESH_S"; do
  printf '  %-40s %s\n' "$k" "$(grep -a -c -F "$k" "$B")"
done
echo
echo "=== 与生产 n4 的大小/md5 对比 ==="
ls -l /home/albus/strata166/data/bin/strata-0.1.54n4 "$B"
md5sum /home/albus/strata166/data/bin/strata-0.1.54n4 "$B"
