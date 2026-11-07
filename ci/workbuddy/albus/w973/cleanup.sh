#!/bin/bash
# 一次性清理：残留挂载 + 宿主 /data + docker 挂载顺序
set -u
say(){ printf '\n=== %s\n' "$*"; }

say "1) 隔离并卸载残留 /mnt/old_home /mnt/old_models"
for p in /mnt/old_home /mnt/old_models; do
  if mountpoint -q "$p"; then
    mount --make-rslave "$p" 2>/dev/null
    umount "$p" 2>/dev/null || umount -l "$p" 2>/dev/null
    printf '  %-18s %s\n' "$p" "$(mountpoint -q "$p" && echo '仍挂载(失败)' || echo '已卸载')"
  else
    printf '  %-18s 未挂载(跳过)\n' "$p"
  fi
  # 每次卸载后立即确认生产两个挂载还在
  printf '    /home/albus: %s | /models: %s\n' \
    "$(mountpoint -q /home/albus && echo OK || echo LOST)" \
    "$(mountpoint -q /models && echo OK || echo LOST)"
  rmdir "$p" 2>/dev/null
done

say "2) 删除宿主根下空壳 /data（只删软链，rmdir 非空会失败）"
if [ -d /data ] && ! mountpoint -q /data; then
  find /data -maxdepth 2 -mindepth 1 -type l -delete 2>/dev/null
  find /data -maxdepth 2 -mindepth 1 ! -type l -print 2>/dev/null | head -5
  rmdir /data/cache 2>/dev/null; rmdir /data 2>/dev/null
  [ -e /data ] && echo "  /data 仍存在（有真实文件，已保留）" || echo "  /data 已删除"
else
  echo "  /data 不存在或已是挂载点，跳过"
fi

say "3) 给 docker 加显式挂载依赖"
mkdir -p /etc/systemd/system/docker.service.d
cat > /etc/systemd/system/docker.service.d/10-mounts.conf <<'EOF'
[Unit]
# 容器把 /home/albus/strata166/data 绑成 /data、/models 只读绑进容器；
# 磁盘搬家后这两个路径是 bind mount，显式声明顺序，避免容器先于挂载启动
RequiresMountsFor=/nvme /home/albus /models
After=home-albus.mount models.mount nvme.mount
EOF
systemctl daemon-reload
echo "  RequiresMountsFor: $(systemctl show docker.service -p RequiresMountsFor --no-pager | cut -d= -f2-)"

say "4) 结果"
for p in /nvme /home/albus /models; do printf '  %-14s ' "$p"; findmnt -no SOURCE,FSTYPE "$p" 2>/dev/null || echo '(未挂载!)'; done
echo "  根卷可用: $(df -h / | tail -1 | awk '{print $4}') | 新盘可用: $(df -h /nvme | tail -1 | awk '{print $4}')"
echo "  生产: $(curl -s -m 3 localhost:8090/health | head -c 40)"
