S=/home/albus/strata166/src028
echo "=== dflash2.cpp: the STRATA_USE_HIP guarded region 1 (190-215) ==="
sed -n '190,215p' "$S/src/core/dflash2.cpp"
echo
echo "=== region 2 (438-460) ==="
sed -n '438,460p' "$S/src/core/dflash2.cpp"
echo
echo "=== our configure line used for the current binary (r02) ==="
sed -n '1,60p' /home/albus/strata166/tmp/r02_cfg.sh 2>/dev/null | cut -c1-160
