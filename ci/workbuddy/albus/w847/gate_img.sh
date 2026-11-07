set +e
S=/home/albus/strata166/tmp/verify_patches.sh
echo "===== [1] 当前门禁的 IMG 默认值 ====="
grep -n "IMG=" "$S" | head -3
cp -a "$S" "$S.bak_w847"
python3 - "$S" <<'PY'
import io,sys,re
p=sys.argv[1]; s=io.open(p,encoding="utf-8").read()
m=re.search(r'^IMG="\$\{3:-([^}]*)\}"', s, re.M)
if not m:
    print("  !! 未找到 IMG 赋值锚点"); sys.exit(0)
old=m.group(0)
new='IMG="${3:-$(docker inspect strata166-407 --format \'{{.Config.Image}}\' 2>/dev/null || echo strata-gfx906:0.2.9)}"   # W847: 默认取运行中的镜像，别再写死 tag'
s=s.replace(old,new,1)
io.open(p,"w",encoding="utf-8").write(s)
print("  patched:/n   ",old,"\n -> ",new)
PY
echo
echo "===== [2] 复跑门禁（应显示 img=strata-gfx906:0.2.9） ====="
bash "$S" 2>&1 | grep -E "img=|GATE|image:|served:" | head -12
echo
echo "===== [3] 反向验证：故意指向旧镜像时是否仍能判（确保没把判定废掉） ====="
bash "$S" /home/albus/strata166/gfx029 /home/albus/strata166/data/bin/strata-0.1.55g "strata-gfx906:0.2.8p2" 2>&1 | grep -E "img=|GATE" | head -3
