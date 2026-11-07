set +e
S=/home/albus/strata166/gfx029
O=/home/albus/strata166/gfx029-build
echo "=== 门禁兼容 shim（让 verify_patches 能按原路径找 build.ninja 与 strata） ==="
ln -sfn "$O" "$S/build-029g"
cp -f "$O/strata-0.1.55g" "$S/strata"
ls -l "$S/build-029g/build.ninja" "$S/strata" | sed 's/^/  /'
echo
echo "=== 门禁（tree=gfx029, bin=0.1.55g） ==="
bash /home/albus/strata166/tmp/verify_patches.sh "$S" "$O/strata-0.1.55g" strata-gfx906:0.2.8p2 2>&1 | tail -22
