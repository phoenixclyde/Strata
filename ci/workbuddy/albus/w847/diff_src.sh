set +e
echo "===== [1] 新镜像 /src 里、树里没有的文件（前 25 个 + 计数） ====="
docker run --rm --entrypoint bash strata-gfx906:0.2.9 -lc 'cd /src && find . -type f | sed "s|^\./||" | sort' > /tmp/img_src.txt 2>/dev/null
( cd /home/albus/strata166/gfx029 && find . -type f -not -path './.git/*' -not -path './build-029g/*' | sed 's|^\./||' | sort ) > /tmp/tree_src.txt
echo -n "  image files: "; wc -l < /tmp/img_src.txt
echo -n "  tree  files: "; wc -l < /tmp/tree_src.txt
echo "  只在镜像里的（stale）:"
comm -23 /tmp/img_src.txt /tmp/tree_src.txt | head -25
echo -n "  stale 总数: "; comm -23 /tmp/img_src.txt /tmp/tree_src.txt | wc -l
echo
echo "  stale 按顶层目录分布:"
comm -23 /tmp/img_src.txt /tmp/tree_src.txt | cut -d/ -f1 | sort | uniq -c | sort -rn | head -10
echo
echo "===== [2] base 镜像里 /src 有没有 .venv / site-packages（决定能不能整体清空 /src） ====="
docker run --rm --entrypoint bash strata-gfx906:0.2.8p2 -lc 'ls -a /src | head -8; ls -d /src/.venv /src/venv 2>/dev/null; python3 -c "import sys;print(sys.prefix)"'
