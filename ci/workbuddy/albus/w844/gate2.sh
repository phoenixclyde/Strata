set +e
S=/home/albus/strata166/tmp/verify_patches.sh
echo "=== 门禁默认 TREE 改为 gfx029（0.2.9 树） ==="
python3 - <<'PY'
import io
p="/home/albus/strata166/tmp/verify_patches.sh"
s=io.open(p,encoding="utf-8").read()
old='TREE="${1:-/home/albus/strata166/src028}"'
new='TREE="${1:-/home/albus/strata166/gfx029}"   # W844: 生产二进制现在由 v0.2.9 树构建（src028 = 旧 0.2.8 树，留作回滚）'
if old in s and "gfx029" not in s:
    s=s.replace(old,new,1); io.open(p,"w",encoding="utf-8").write(s); print("patched TREE default")
else:
    print("no change (already gfx029 or anchor missing)")
PY
echo
echo "=== 跑门禁（默认参数） ==="
bash "$S" 2>&1 | tail -22
