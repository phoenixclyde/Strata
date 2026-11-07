set +e
C=strata166-407
D=/home/albus/strata166/gfx029
echo "===== [1] 现在镜像里的 terminal/seed 是什么 ====="
docker exec "$C" bash -lc 'ls /opt/strata 2>/dev/null; echo "-- terminal:"; ls /opt/strata/terminal 2>/dev/null | head; echo "-- seed:"; ls /opt/strata/seed 2>/dev/null | head; echo "-- /usr/local/bin/strata:"; head -5 /usr/local/bin/strata 2>/dev/null'
echo
echo "===== [2] 0.2.8p2 base 里同一个位置 ====="
docker run --rm --entrypoint bash strata-gfx906:0.2.8p2 -lc 'du -sh /opt/strata/* 2>/dev/null; ls /opt/strata/terminal/bin 2>/dev/null | head -4'
echo
echo "===== [3] package_terminal.py 用法 ====="
sed -n '1,40p' "$D/packaging/package_terminal.py"
echo
echo "===== [4] 它需要什么（网络/缓存/pip） ====="
grep -nE "add_argument|pip|venv|download|wheel|cache" "$D/packaging/package_terminal.py" | head -20
