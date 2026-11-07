import sys
sys.path.insert(0, r"D:/workbuddy_space/strata_ws/deploy/params")
import _sshutil
S = r'''
R=/home/albus/strata166/pr/k10
echo "=== git dir / hooks actual ==="
git -C $R rev-parse --git-common-dir --git-dir
GD=$(git -C $R rev-parse --git-common-dir)
ls -la $GD/hooks | grep -v sample | head -30
echo "=== pre-push content ==="
sed -n '1,120p' $GD/hooks/pre-push 2>/dev/null
echo "=== branches w1046 ==="
for b in origin/ci/w1046-gates origin/ci/w1046-hooks; do
  echo "-- $b"
  git -C $R log --oneline -4 $b
  git -C $R diff --stat af797b90..$b | tail -30
done
echo "=== ci/w1046-gates file list ==="
git -C $R diff --name-status af797b90..origin/ci/w1046-gates
echo "=== ci/w1046-hooks file list ==="
git -C $R diff --name-status af797b90..origin/ci/w1046-hooks
echo "=== current production branch status ==="
git -C $R status -sb | head -5
git -C $R rev-parse --short HEAD
'''
rc,out,err=_sshutil.run_remote(S,timeout=180)
print(out)
if err.strip(): print("ERR",err[-1000:])
raise SystemExit(rc)
