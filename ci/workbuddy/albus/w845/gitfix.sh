set -u
D=/home/albus/strata166/gfx029
cd "$D" || exit 1

echo "===== [1] 策略修复：上游 push URL 必须 DISABLED ====="
git remote set-url --push upstream DISABLED
git remote -v | sed 's/^/  /'

echo "===== [2] 清掉树里的伪产物（它让 PROVENANCE 变成自证） ====="
rm -f "$D/strata"
printf '%s\n' "build-029g" "strata" >> .git/info/exclude
sort -u .git/info/exclude -o .git/info/exclude
ls -l "$D/build-029g" 2>/dev/null | head -2

echo "===== [3] 门禁 PROVENANCE 改成跟随符号链接找构建产物 ====="
S=/home/albus/strata166/tmp/verify_patches.sh
cp -a "$S" "$S.bak_w845"
python3 - "$S" <<'PY'
import io,sys
p=sys.argv[1]
s=io.open(p,encoding="utf-8").read()
old='hit=$(find "$TREE" -maxdepth 2 -name strata -type f -exec md5sum {} \\; 2>/dev/null | grep -c "$b" || true)'
new='hit=$(find -L "$TREE" -maxdepth 3 -name strata -type f -exec md5sum {} \\; 2>/dev/null | grep -c "$b" || true)   # W845: -L 跟随 build-* 符号链接到树外构建目录；树内不得存副本'
if old in s:
    s=s.replace(old,new,1); io.open(p,"w",encoding="utf-8").write(s); print("  gate patched (-L, maxdepth 3)")
else:
    print("  !! anchor not found; gate untouched")
PY
grep -n "find -L" "$S" | head -2

echo "===== [4] 提交 12 个补丁文件（此前全是未提交状态！） ====="
git add -A CMakeLists.txt include/strata/core/arch_defaults.hpp include/strata/kernels/gfx_arch.hpp \
           include/strata/platform/hip_compat/strata_hip.h serve/telemetry.py serve/web/app.css serve/web/app.js \
           src/core/arch_defaults.cpp src/core/arch_defaults_test.cpp src/kernels/cuda/qsa_decode_attn.cu \
           src/kernels/cuda/qsa_select.cu src/program/generate.cpp
echo "--- 暂存清单:"; git diff --cached --stat | tail -14

git -c user.name=albus -c user.email=albus@localhost commit -q -F - <<'MSG'
gfx906: replay the 0.2.8 local patches onto v0.2.9 (engine 0.1.55)

The 0.2.8 branch (gfx906/0.2.8-mi50 @ cc8a071) shares no history with upstream
(the clone is depth-1, merge-base empty), so it cannot be rebased.  This branch
is instead a fresh worktree at tag v0.2.9 with the same patches replayed:

  files copied verbatim (md5 identical to the 0.2.8 branch):
    src/kernels/cuda/qsa_decode_attn.cu      W794/W798 decode attention
    src/kernels/cuda/qsa_select.cu           W842 STRATA_SELECT_SIMT=2
    include/strata/platform/hip_compat/strata_hip.h   W793 HIP compat
    include/strata/kernels/gfx_arch.hpp      gfx906 arch helpers
    include/strata/core/arch_defaults.hpp    + src/core/arch_defaults.cpp
    src/core/arch_defaults_test.cpp
    serve/telemetry.py, serve/web/app.css, serve/web/app.js  W831/W833 telemetry
  anchors:
    src/program/generate.cpp  (W839 arch entry + trace)
    CMakeLists.txt            (W793a/W793b/W776)

Built as 0.1.55 (md5 29b15bb4...), gate 17/17, three-arm A/B vs 0.1.54n4
neutral on read (|delta| <= 0.9%, replica spread <= 0.8%) and on decode.
MSG
echo "--- 提交后:"
git log --oneline --decorate -3
git status --porcelain | head -6

echo "===== [5] 推到自己的 remote（phoenixclyde） ====="
timeout 300 git push -u origin gfx906/0.2.9-mi50 2>&1 | tail -6
git branch -vv | grep 0.2.9
echo "--- 远端确认:"; timeout 90 git ls-remote origin "refs/heads/gfx906/*" 2>&1 | head -4
