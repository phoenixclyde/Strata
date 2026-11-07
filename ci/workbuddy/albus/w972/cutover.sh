#!/bin/bash
# Phase B: cut over /home/albus and /models to the NVMe, keeping the paths identical.
# Order: stop the three consumers -> final delta -> verify -> rename old -> bind mount -> fstab -> start -> verify.
set -u
cd /

echo "== 1. 停三个有绑定挂载的容器 =="
docker stop strata166-407 comfyui-cu130 searxng > /dev/null
docker ps --format "{{.Names}}" | tr '\n' ' '; echo

echo "== 2. 收尾增量 =="
sudo ionice -c2 -n7 nice -n19 rsync -aHAX --numeric-ids --delete /home/albus/ /nvme/home_albus/ 2>&1 | tail -3
sudo ionice -c2 -n7 nice -n19 rsync -aHAX --numeric-ids --delete /models/ /nvme/models/ 2>&1 | tail -3

echo "== 3. 校验（字节数 + 文件数）=="
for pair in "/home/albus /nvme/home_albus" "/models /nvme/models"; do
  set -- $pair
  a=$(sudo du -sx --block-size=1 "$1" | cut -f1)
  b=$(sudo du -sx --block-size=1 "$2" | cut -f1)
  fa=$(sudo find "$1" -xdev | wc -l)
  fb=$(sudo find "$2" -xdev | wc -l)
  printf "%-16s src=%sB/%s files  dst=%sB/%s files  %s\n" "$1" "$a" "$fa" "$b" "$fb" \
    "$([ "$a" = "$b" ] && echo OK || echo DIFF)"
done

echo "== 4. 旧目录改名（不动数据，只腾出路径）=="
sudo mv /home/albus /home/albus.old
sudo mv /models /models.old

echo "== 5. 建挂载点 + 绑定挂载 =="
sudo mkdir -p /home/albus /models
sudo mount --bind /nvme/home_albus /home/albus
sudo mount --bind /nvme/models /models
findmnt -no SOURCE,TARGET,FSTYPE /home/albus /models

echo "== 6. 写 fstab（幂等）=="
sudo cp -n /etc/fstab /etc/fstab.bak_w972
if ! grep -q "LABEL=nvme1" /etc/fstab; then
  sudo tee -a /etc/fstab > /dev/null <<'EOF'
# NVMe (KIOXIA EXCERIA PLUS G4 2TB, xfs 4Kn) — added 2026-11-04
UUID=22a2f408-ea0d-4423-8f6f-aa9db2b72f0c /nvme          xfs  defaults,noatime,nofail  0 2
/nvme/home_albus /home/albus none bind,nofail,x-systemd.requires-mounts-for=/nvme 0 0
/nvme/models     /models     none bind,nofail,x-systemd.requires-mounts-for=/nvme 0 0
EOF
fi
tail -4 /etc/fstab
sudo systemctl daemon-reload

echo "== 7. 起容器 =="
docker start strata166-407 comfyui-cu130 searxng > /dev/null
for i in $(seq 1 90); do
  r=$(curl -s -m 3 localhost:8090/health || true)
  case "$r" in *'"loaded": true'*) echo "strata UP after $((i*4))s"; break;; esac
  sleep 4
done
curl -s -m 3 localhost:8090/health | head -c 120; echo

echo "== 8. 落盘校验 =="
df -hT /home/albus /models /nvme | tail -3
sudo md5sum /nvme/models/huihui-ai/Huihui-Qwen3.8-Flash-Next-abliterated-GGUF/unsloth-UD-Q4_K_XL/Qwen3.8-Flash-Next-UD-Q4_K_XL-00001-of-00004.gguf 2>/dev/null | cut -c1-32
ls -ld /home/albus/.ssh; sudo stat -c "%U:%G %a %n" /home/albus/.ssh/authorized_keys 2>/dev/null
