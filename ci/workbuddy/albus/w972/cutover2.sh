#!/bin/bash
# Phase B (v2): cut over with ALL containers stopped, so the verification reference is frozen.
# Paths stay identical -> containers need only a restart.
set -u
cd /

echo "== 1. 停全部容器（冻结写入，保证校验基准）=="
docker stop $(docker ps -q) > /dev/null
docker ps -a --format "{{.Names}} {{.Status}}" | head -8

echo "== 2. 收尾增量（含删除多余项）=="
sudo ionice -c2 -n7 nice -n19 rsync -aHAX --numeric-ids --delete /home/albus/ /nvme/home_albus/ 2>&1 | tail -3
sudo ionice -c2 -n7 nice -n19 rsync -aHAX --numeric-ids --delete /models/   /nvme/models/     2>&1 | tail -3

echo "== 3. 旧目录改名（数据仍在原地，只是让出路径）=="
sudo mv /home/albus /home/albus.old
sudo mv /models /models.old

echo "== 4. 挂载点 + 绑定挂载 =="
sudo mkdir -p /home/albus /models
sudo mount --bind /nvme/home_albus /home/albus
sudo mount --bind /nvme/models /models
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

echo "== 7. 挂载与权限 =="
df -hT /home/albus /models /nvme | tail -3
ls -ld /home/albus/.ssh
sudo stat -c "%U:%G %a %n" /home/albus/.ssh/authorized_keys
