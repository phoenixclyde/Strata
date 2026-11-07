set +e
D=/home/albus/strata166/gfx029
cd "$D" || exit 1
echo "===== [1] 旧分支的树到底是 0.2.8 还是 0.2.9？ ====="
echo -n "  serve/replicas.py（0.2.9 才有）在旧分支里: "
git cat-file -e gfx906/0.2.8-mi50:serve/replicas.py 2>/dev/null && echo "存在 ⇒ 旧分支树 = 0.2.9" || echo "不存在 ⇒ 旧分支树 = 0.2.8"
echo -n "  serve/replicas.py 在 v0.2.9 里: "
git cat-file -e v0.2.9:serve/replicas.py 2>/dev/null && echo "有" || echo "无"
echo
echo "===== [2] 旧分支 vs v0.2.9 的净差异（文件数） ====="
git diff --stat v0.2.9 gfx906/0.2.8-mi50 | tail -4
echo
echo "===== [3] 旧分支 vs 新分支的树差异（应为 0） ====="
echo -n "  diff 行数 = "; git diff gfx906/0.2.8-mi50 gfx906/0.2.9-mi50 | wc -l
echo
echo "===== [4] 旧分支的 6 个提交 ====="
git log --oneline upstream/main..gfx906/0.2.8-mi50 | sed 's/^/  /'
echo
echo "===== [5] 补写 rebase 助手（上一轮被 SIGTERM 截断没写成） ====="
cat > /home/albus/strata166/tmp/rebase_gfx906.sh <<'EOS'
#!/bin/bash
# gfx906 分支跟上游。正常路径：git rebase（仓库已 unshallow，merge-base 可算）。
# 兜底：若仓库又被弄成浅克隆（merge-base 为空），用 --onto 显式给旧基点。
set -u
D=${D:-/home/albus/strata166/gfx029}
REF=${1:-upstream/main}
cd "$D" || exit 1
git fetch upstream --tags >/dev/null 2>&1 || { echo "fetch tags failed"; exit 1; }
git fetch upstream >/dev/null 2>&1 || { echo "fetch failed"; exit 1; }
if [ "$(git rev-parse --is-shallow-repository)" = "true" ]; then
  echo "!! shallow repo: rebase needs merge-base; run 'git fetch --unshallow upstream' first" >&2
  exit 2
fi
MB=$(git merge-base HEAD "$REF" 2>/dev/null || true)
[ -z "$MB" ] && { echo "!! no merge-base with $REF (unrelated history)"; exit 3; }
echo "base=$(echo "$MB" | cut -c1-8)  ours=$(git rev-list --count "$REF"..HEAD) commit(s)"
git rebase "$REF" || { echo "!! conflicts: resolve, then 'git rebase --continue'"; exit 4; }
echo "--- after:"; git log --oneline --decorate -3
EOS
chmod +x /home/albus/strata166/tmp/rebase_gfx906.sh
ls -l /home/albus/strata166/tmp/rebase_gfx906.sh | sed 's/^/  /'
bash /home/albus/strata166/tmp/rebase_gfx906.sh 2>&1 | tail -6
echo
echo "===== [6] 远端跟踪引用 ====="
git rev-parse --short refs/remotes/origin/gfx906/0.2.9-mi50 2>/dev/null
git branch -vv | grep 0.2.9 | sed 's/^/  /'
