set +e
D=/home/albus/strata166/gfx029
cd "$D" || exit 1
echo "===== [1] 远端跟踪引用到底有没有 ====="
git for-each-ref refs/remotes/origin | grep -E "0\.2\.(8|9)" | sed 's/^/  /'
echo "--- ls-remote 真值:"; timeout 90 git ls-remote origin "refs/heads/gfx906/0.2.9-mi50" 2>&1 | sed 's/^/  /'
echo "--- 本地 HEAD:"; git rev-parse HEAD | sed 's/^/  /'
echo
echo "===== [2] 若缺，补 fetch + 设跟踪 ====="
timeout 120 git fetch origin "+refs/heads/*:refs/remotes/origin/*" 2>&1 | tail -3
git branch --set-upstream-to=origin/gfx906/0.2.9-mi50 gfx906/0.2.9-mi50 2>&1 | tail -2
git branch -vv | grep 0.2.9 | sed 's/^/  /'
echo
echo "===== [3] 树哈希（作为产物出处凭据） ====="
echo "  commit   = $(git rev-parse --short HEAD)"
echo "  tree     = $(git rev-parse HEAD^{tree})"
echo "  产物 md5 = $(md5sum /home/albus/strata166/data/bin/strata-0.1.55g | cut -d' ' -f1)"
echo "  构建目录 md5 = $(md5sum /home/albus/strata166/gfx029-build/strata-0.1.55g | cut -d' ' -f1)"
echo "  构建时间 = $(ls -l --time-style=+%m-%d_%H:%M /home/albus/strata166/gfx029-build/strata-0.1.55g | awk '{print $6}')"
echo
echo "===== [4] 最近一次提交的文件是否与工作区一致 ====="
git diff --stat HEAD | wc -l
