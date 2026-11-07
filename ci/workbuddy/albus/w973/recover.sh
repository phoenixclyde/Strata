#!/bin/bash
# 恢复后一次性复核：挂载 / 残留 / 生产 / 数据完整性
set -u
say(){ printf '\n=== %s\n' "$*"; }

say "1) 三个挂载"
for p in /nvme /home/albus /models; do
  printf '  %-12s ' "$p"
  findmnt -no SOURCE,FSTYPE,PROPAGATION "$p" 2>/dev/null || echo "MISSING"
done

say "2) 若缺则补挂（幂等）"
mountpoint -q /home/albus || mount --bind /nvme/home_albus /home/albus
mountpoint -q /models     || mount --bind /nvme/models /models
for p in /home/albus /models; do mount --make-private "$p" 2>/dev/null; done
for p in /nvme /home/albus /models; do
  printf '  %-12s ' "$p"
  findmnt -no SOURCE,TARGET "$p" 2>/dev/null || echo "STILL MISSING"
done

say "3) 清残留 /mnt/old_*（先断传播再卸，逐个确认）"
for p in /mnt/old_home /mnt/old_models; do
  if mountpoint -q "$p"; then
    mount --make-private "$p" || true
    umount "$p" || umount -l "$p"
    sleep 1
    printf '  %-16s %s | /home/albus=%s /models=%s\n' "$p" \
      "$(mountpoint -q "$p" && echo '仍挂载' || echo '已卸载')" \
      "$(mountpoint -q /home/albus && echo OK || echo LOST)" \
      "$(mountpoint -q /models && echo OK || echo LOST)"
    rmdir "$p" 2>/dev/null
  else
    printf '  %-16s 未挂载\n' "$p"
  fi
done

say "4) 宿主机 /data"
[ -e /data ] && echo "  仍存在（需查）" || echo "  已删除"

say "5) 生产与数据"
echo "  health: $(curl -s -m 3 localhost:8090/health | head -c 60)"
docker exec strata166-407 md5sum /data/bin/strata-0.1.56-080 2>/dev/null
docker exec strata166-407 ls /data/packs/ 2>/dev/null
docker exec strata166-407 df -hT /data /models 2>/dev/null | tail -2
echo "  容器挂载: $(docker inspect -f '{{range .Mounts}}{{.Source}}->{{.Destination}} {{end}}' strata166-407)"
echo "  docker 依赖: $(systemctl show docker.service -p RequiresMountsFor --no-pager | cut -d= -f2-)"
echo "  根卷: $(df -h / | tail -1 | awk '{print $4}') free | 新盘: $(df -h /nvme | tail -1 | awk '{print $4}') free"
