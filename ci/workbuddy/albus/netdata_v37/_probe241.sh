#!/bin/bash
# 实测 SATA 属性 241 (Total_LBAs_Written) 的**真实单位**：
# 写入已知字节数，看计数涨多少 => 单位 = 字节 / 增量。不猜。
set -u
ATTR='^ *(241|242|180|187|199|231) '
echo "### DF"
df -h /tmp / | cat

echo "### BEFORE"
docker exec netdata /usr/sbin/smartctl -A /dev/sda | grep -E "$ATTR"

echo "### WRITE 256MiB"
dd if=/dev/zero of=/tmp/_smtest.bin bs=1M count=256 conv=fsync 2>&1 | tail -2
sync
sleep 2

echo "### AFTER"
docker exec netdata /usr/sbin/smartctl -A /dev/sda | grep -E "$ATTR"

echo "### CLEANUP"
rm -f /tmp/_smtest.bin
sync
df -h /tmp | tail -1
