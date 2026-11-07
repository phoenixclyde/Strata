#!/bin/bash
# 建 gfx906 构建修复分支并推到 fork（只改 2 个文件）
set +e
D=/home/albus/strata166/pr
FK=git@github.com:phoenixclyde/Strata.git
BR=gfx906-build-fixes-402

mkdir -p $D
cd $D

echo "===== [1] clone fork（shallow, main）====="
if [ ! -d $D/strata-fork/.git ]; then
  rm -rf $D/strata-fork
  git clone --depth 1 --branch main $FK $D/strata-fork 2>&1 | tail -4
else
  echo "  已存在，重置"
  git -C $D/strata-fork fetch --depth 1 origin main 2>&1 | tail -2
  git -C $D/strata-fork checkout -B main origin/main 2>&1 | tail -2
fi
R=$D/strata-fork
echo -n "  HEAD = "; git -C $R rev-parse HEAD
echo -n "  与上游 tag v0.1.40.2 对比: "
git -C $R rev-parse HEAD

echo
echo "===== [2] 建分支 ====="
git -C $R checkout -B $BR 2>&1 | tail -2
git -C $R rev-parse --abbrev-ref HEAD

echo
echo "===== [3] 打补丁（H5 打 + H6 打；H1~H4 只验证）====="
python3 $D/patch_gfx906_402.py --root $R 2>&1 | tail -22
echo "patch_rc=$?"

echo
echo "===== [4] 改动清单（应恰 2 个文件）====="
git -C $R status --porcelain
echo "--- numstat ---"
git -C $R diff --numstat
echo "--- 全文 diff ---"
git -C $R diff

echo
echo "===== [5] commit ====="
git -C $R config user.name phoenixclyde
git -C $R config user.email "phoenixclyde@users.noreply.github.com"
git -C $R add -A
git -C $R commit -F $D/commitmsg.txt 2>&1 | tail -5
echo -n "  新 HEAD = "; git -C $R rev-parse HEAD
git -C $R log -1 --format="  author=%an <%ae>%n  subject=%s"

echo
echo "===== [6] push 到 fork ====="
git -C $R push $FK "HEAD:refs/heads/$BR" 2>&1 | tail -6
echo "  push_rc=$?"

echo
echo "===== [7] 远端核对 ====="
git ls-remote --heads $FK 2>/dev/null | sed 's/^/  /'
echo -n "  本地 = "; git -C $R rev-parse HEAD
