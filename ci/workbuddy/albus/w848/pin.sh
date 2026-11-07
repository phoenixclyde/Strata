set +e
D=/home/albus/strata166/gfx029
echo "===== [1] PBS pin（要下载哪个 CPython） ====="
grep -nE "PBS_RELEASE|PBS_BASE|\"file\"|sha256" "$D/packaging/package_terminal.py" | head -14
echo
echo "===== [2] setup.py 有没有镜像/代理支持（github 被墙时） ====="
grep -nE "gh-proxy|GH_PROXY|MIRROR|mirror|STRATA_GITHUB|github.com" "$D/setup.py" | head -12
echo
echo "===== [3] fetch_python 的缓存行为（预放文件能不能跳过下载） ====="
sed -n '/^def fetch_python/,/^def /p' "$D/packaging/package_terminal.py" | head -30
