set +e
echo "=== ab_p37.sh ==="
cat /home/albus/strata166/tmp/ab_p37.sh
echo
echo "=== 是否有部署/重启脚本 ==="
ls -l /home/albus/strata166/tmp/ | grep -iE "deploy|restart|switch|serve|cfg" | head -20
