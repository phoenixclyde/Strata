#!/bin/bash
# NVMe 时代的 I/O 策略（持久化 + 立即生效）
set -u
say(){ printf '\n=== %s\n' "$*"; }

say "1) 内存回收策略：保护 71.7 GiB expert arena 不被换出"
cat > /etc/sysctl.d/99-strata-nvme.conf <<'EOF'
# NVMe 迁移后的读多写少策略（W975）
# arena 是 71.7 GiB 匿名页，一旦被回收换到 swap，decode 会退化到毫秒级抖动
vm.swappiness = 10
# 保留 inode/dentry 缓存（模型分片数少，但 pack 目录深）
vm.vfs_cache_pressure = 50
# 读为主，写只发生在日志/profile：把脏页阈值设成绝对字节，避免大 RAM 上一次性回写 20%
vm.dirty_background_bytes = 268435456
vm.dirty_bytes = 1073741824
EOF
sysctl -p /etc/sysctl.d/99-strata-nvme.conf 2>&1 | sed 's/^/  /'

say "2) NVMe 预读：128 KB -> 2 MB（顺序填充 arena 时生效）"
cat > /etc/udev/rules.d/60-nvme-readahead.rules <<'EOF'
# W975: NVMe 顺序读峰值 2.4 GB/s，128 KB 预读偏小；2048 KB 适配 arena 填充与冷读
ACTION=="add|change", KERNEL=="nvme0n1", ATTR{queue/read_ahead_kb}="2048"
EOF
echo 2048 > /sys/block/nvme0n1/queue/read_ahead_kb
udevadm control --reload-rules 2>/dev/null
printf '  read_ahead_kb = %s\n' "$(cat /sys/block/nvme0n1/queue/read_ahead_kb)"
printf '  scheduler     = %s\n' "$(cat /sys/block/nvme0n1/queue/scheduler)"
printf '  nr_requests   = %s\n' "$(cat /sys/block/nvme0n1/queue/nr_requests)"

say "3) 当前内存"
free -g | head -2
