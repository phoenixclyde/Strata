set +e
R=/home/albus/strata166/gfx906
D=/home/albus/strata166/gfx029
echo "===== [1] gfx029 分支与工作区 ====="
git -C "$D" log -1 --format='HEAD=%h %d %s'
echo -n "branch: "; git -C "$D" rev-parse --abbrev-ref HEAD
echo "--- status（前 20）:"
git -C "$D" status --porcelain | head -20
echo -n "status 行数: "; git -C "$D" status --porcelain | wc -l
echo -n "ahead/behind vs v0.2.9: "; git -C "$D" rev-list --left-right --count v0.2.9...HEAD 2>/dev/null
echo "--- 最近 3 提交（含 tag 关系）:"
git -C "$D" log --oneline --decorate -3
echo
echo "===== [2] UPSTREAM 与浅克隆状态 ====="
echo -n "is-shallow(gfx906): "; git -C "$R" rev-parse --is-shallow-repository
echo -n "is-shallow(gfx029): "; git -C "$D" rev-parse --is-shallow-repository
echo "shallow 文件内容行数: $(wc -l < "$R/.git/shallow" 2>/dev/null)"
echo "--- remotes(gfx906):"; git -C "$R" remote -v
echo "--- remotes(gfx029):"; git -C "$D" remote -v
echo "--- upstream/main = $(git -C "$D" rev-parse --short upstream/main 2>/dev/null)  v0.2.9 = $(git -C "$D" rev-parse --short v0.2.9 2>/dev/null)"
echo -n "merge-base(HEAD,upstream/main) = "; git -C "$D" merge-base HEAD upstream/main 2>/dev/null | cut -c1-10 || echo "(空)"
echo "--- v0.2.9 的父提交: $(git -C "$D" rev-list --parents -1 v0.2.9 2>/dev/null)"
echo
echo "===== [3] 分支是否已推到自己的 remote ====="
git -C "$D" branch -vv | head -6
echo "--- ls-remote phoenixclyde 上的同名分支:"
timeout 60 git -C "$D" ls-remote phoenixclyde "refs/heads/gfx906/*" 2>&1 | head -6
echo
echo "===== [4] 仓库体积 ====="
du -sh "$R/.git" 2>/dev/null
du -sh "$D" 2>/dev/null
echo
echo "===== [5] 补丁文件是否在产物里（抽样） ====="
for f in src/kernels/cuda/qsa_decode_attn.cu src/kernels/cuda/qsa_select.cu serve/telemetry.py src/core/arch_defaults.cpp; do
  printf '  %-42s md5=%s  W839=%s\n' "$f" "$(md5sum "$D/$f" 2>/dev/null | cut -c1-8)" "$(grep -c 'W839 local' "$D/$f" 2>/dev/null)"
done
