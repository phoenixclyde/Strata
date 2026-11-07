#!/bin/bash
# Free the old copies on the root LV. Deletes through /mnt/rootraw (a private bind of /, i.e. the
# underlying root filesystem), so the live /home/albus and /models mounts on the NVMe are untouched.
set -u
echo "== 前置检查 =="
a=$(stat -c %d /mnt/rootraw/home/albus); b=$(stat -c %d /nvme/home_albus)
echo "dev old=$a  dev new=$b  (必须不同)"
[ "$a" = "$b" ] && { echo "ABORT: same device, refuse to delete"; exit 1; }
echo -n "new home size: "; du -sh /nvme/home_albus 2>/dev/null | cut -f1
echo -n "new models size: "; du -sh /nvme/models 2>/dev/null | cut -f1
test -d /nvme/home_albus/strata166/pr/strata-fork/.git || { echo "ABORT: repo missing on new disk"; exit 1; }
echo "pre-check OK"
echo "root before: $(df -h / | tail -1 | awk '{print $4" free"}')"

echo "== 删除旧数据 =="
sudo find /mnt/rootraw/home/albus -mindepth 1 -maxdepth 1 -exec rm -rf {} + 
sudo find /mnt/rootraw/models      -mindepth 1 -maxdepth 1 -exec rm -rf {} +
echo "delete rc=$?"

echo "root after : $(df -h / | tail -1 | awk '{print $4" free"}')"
echo "new still  : $(df -h /home/albus | tail -1 | awk '{print $4" free"}')"
