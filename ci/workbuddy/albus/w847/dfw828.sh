set +e
echo "===== Dockerfile.w828 全文 ====="
cat /home/albus/strata166/src028/Dockerfile.w828
echo
echo "===== 有没有别的 w8xx Dockerfile ====="
ls -lt --time-style=+%m-%d_%H:%M /home/albus/strata166/src028/Dockerfile* 2>/dev/null
ls -lt --time-style=+%m-%d_%H:%M /home/albus/strata166/gfx029/Dockerfile* 2>/dev/null
