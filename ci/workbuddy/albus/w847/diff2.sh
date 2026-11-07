set +e
docker run --rm --entrypoint bash strata-gfx906:0.2.9 -lc 'cd /src && find . -type f -print0 | xargs -0 -n1 echo' 2>/dev/null | sed 's|^\./||' | LC_ALL=C sort -u > /tmp/i.txt
( cd /home/albus/strata166/gfx029 && find . -type f -not -path './.git/*' -not -path './build-029g/*' | sed 's|^\./||' | LC_ALL=C sort -u ) > /tmp/t.txt
echo -n "image=$(wc -l < /tmp/i.txt)  tree=$(wc -l < /tmp/t.txt)"
echo
echo "=== 只在镜像里（stale，前 20） ==="
LC_ALL=C comm -23 /tmp/i.txt /tmp/t.txt | head -20
echo -n "  stale 总数: "; LC_ALL=C comm -23 /tmp/i.txt /tmp/t.txt | wc -l
echo "  stale 顶层分布:"; LC_ALL=C comm -23 /tmp/i.txt /tmp/t.txt | cut -d/ -f1 | sort | uniq -c | sort -rn | head -8
echo
echo "=== 只在树里（镜像缺，前 20） ==="
LC_ALL=C comm -13 /tmp/i.txt /tmp/t.txt | head -20
echo -n "  缺失总数: "; LC_ALL=C comm -13 /tmp/i.txt /tmp/t.txt | wc -l
echo
echo "=== 关键运行时文件是否在 ==="
for f in data/expert-profile.bin serve/server.py serve/web/index.html bin/strata; do
  printf '  %-30s %s\n' "$f" "$(docker run --rm --entrypoint bash strata-gfx906:0.2.9 -lc "ls -l /src/$f 2>/dev/null | awk '{print \$5}'" )"
done
echo "--- 树里 data/ 内容:"; ls -l /home/albus/strata166/gfx029/data | head -6
