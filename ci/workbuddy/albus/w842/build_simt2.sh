set +e
cd /home/albus/strata166/gfx906 || exit 1
git -c user.name=albus -c user.email=albus@166 commit -am "gfx906: STRATA_SELECT_SIMT=2 on HIP (port of upstream #3073); =2 took the warp kernel before" 2>&1 | tail -3
echo "--- head:"; git rev-parse --short HEAD
echo
echo "=== sync 进构建树 ==="
bash /home/albus/strata166/tmp/sync_gfx906.sh 2>&1 | tail -8
echo
echo "=== 增量编译 ==="
cd /home/albus/strata166/src028/build-028r || exit 1
(sudo -n ninja strata 2>&1 || ninja strata 2>&1) | tail -25
echo "=== 产物 ==="
ls -l --time-style=+%H:%M strata 2>/dev/null
md5sum strata 2>/dev/null
echo "=== 部署物（对照，不应变） ==="
md5sum /home/albus/strata166/data/bin/strata-0.1.54n3
