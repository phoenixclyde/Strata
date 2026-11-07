#!/bin/bash
# 找 SATA 盘上「已写入字节数」的权威来源：Device Statistics log (GP Log 0x04) 是 ACS 标准字段
set -u
echo "### DEVSTAT"
docker exec netdata /usr/sbin/smartctl -l devstat /dev/sda 2>&1 | sed -n '1,60p'
echo
echo "### DEVSTAT -p sct"
docker exec netdata /usr/sbin/smartctl -l devstat,pages=0x04 /dev/sda 2>&1 | sed -n '1,12p'
echo
echo "### HEALTH"
docker exec netdata /usr/sbin/smartctl -H /dev/sda 2>&1 | tail -4
echo
echo "### 241/242 再看一次（确认是否只是更新慢）"
docker exec netdata /usr/sbin/smartctl -A /dev/sda | grep -E '^ *(241|242) '
