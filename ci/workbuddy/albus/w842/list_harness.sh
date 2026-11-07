set +e
ls /home/albus/strata166/tmp/*.py | head -40
echo "=== mt_gen.py 头部 ==="
head -25 /home/albus/strata166/tmp/mt_gen.py 2>/dev/null
echo "=== 有没有 read/ttft 测速脚本 ==="
ls /home/albus/strata166/tmp/ | grep -iE "read|ttft|bench|mt_" | head -20
