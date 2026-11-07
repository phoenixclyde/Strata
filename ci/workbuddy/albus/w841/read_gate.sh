set +e
echo "=== tmp 脚本清单 ==="
ls -l /home/albus/strata166/tmp/ | head -40
echo
echo "=== PROVENANCE 判定逻辑 ==="
grep -n -B4 -A18 "PROVENANCE" /home/albus/strata166/tmp/verify_patches.sh
echo
echo "=== verify_patches.sh 头部 ==="
sed -n '1,40p' /home/albus/strata166/tmp/verify_patches.sh
