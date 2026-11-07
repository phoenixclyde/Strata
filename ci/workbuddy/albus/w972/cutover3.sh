#!/bin/bash
# Phase B (v3): switch /home/albus and /models to the NVMe with NO missing-path window.
#   * the old trees stay reachable through /mnt/old_* (bind pins them), so they can serve as the
#     verification reference and even be deleted later without ever unmounting the live paths;
#   * containers only restart, every bind path stays identical.
set -u
cd /

echo "== 1. 停全部容器 =="
docker stop $(docker ps -q) > /dev/null
echo "remaining: $(docker ps --format '{{.Names}}' | wc -l)"

echo "== 2. 固定旧树引用 =="
sudo mkdir -p /mnt/old_home /mnt/old_models
sudo mount --bind /home/albus /mnt/old_home
sudo mount --bind /models     /mnt/old_models
findmnt -no SOURCE,TARGET /mnt/old_home /mnt/old_models

echo "== 3. 收尾增量（从冻结的旧树）=="
sudo ionice -c2 -n7 nice -n19 rsync -aHAX --numeric-ids --delete /mnt/old_home/ /nvme/home_albus/ 2>&1 | tail -2
sudo ionice -c2 -n7 nice -n19 rsync -aHAX --numeric-ids --delete /mnt/old_models/ /nvme/models/   2>&1 | tail -2

echo "== 4. 覆盖挂载（瞬时切换，路径不消失）=="
sudo mount --bind /nvme/home_albus /home/albus
sudo mount --bind /nvme/models     /models
findmnt -no SOURCE,TARGET,FSTYPE /home/albus /models

echo "== 5. fstab（幂等）=="
sudo cp -n /etc/fstab /etc/fstab.bak_w972
if ! grep -q "LABEL=nvme1" /etc/fstab; then
  sudo tee -a /etc/fstab > /dev/null <<'EOF'
# NVMe (KIOXIA EXCERIA PLUS G4 2TB, xfs 4Kn) - added 2026-11-04
UUID=22a2f408-ea0d-4423-8f6f-aa9db2b72f0c /nvme          xfs  defaults,noatime,nofail  0 2
/nvme/home_albus /home/albus none bind,nofail,x-systemd.requires-mounts-for=/nvme 0 0
/nvme/models     /models     none bind,nofail,x-systemd.requires-mounts-for=/nvme 0 0
EOF
fi
sudo systemctl daemon-reload

echo "== 6. 起全部容器 =="
docker start $(docker ps -aq) > /dev/null
for i in $(seq 1 90); do
  r=$(curl -s -m 3 localhost:8090/health || true)
  case "$r" in *'"loaded": true'*) echo "strata UP after $((i*4))s"; break;; esac
  sleep 4
done
curl -s -m 3 localhost:8090/health | head -c 120; echo

echo "== 7. 权限与挂载 =="
df -hT /home/albus /models | tail -2
sudo stat -c "%U:%G %a %n" /home/albus/.ssh /home/albus/.ssh/authorized_keys
