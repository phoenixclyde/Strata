#!/bin/bash
# 重启前加固：容器自启收敛 + SSH 后备公钥（放根卷）
set -u
say(){ printf '\n=== %s\n' "$*"; }

say "1) 历史实验容器 -> restart=no（只保留 6 个生产/服务容器）"
KEEP=" strata166-407 searxng netdata open-webui comfyui-cu130 portainer "
for c in $(docker ps -a --format '{{.Names}}'); do
  case "$KEEP" in *" $c "*) continue;; esac
  r=$(docker inspect -f '{{.HostConfig.RestartPolicy.Name}}' "$c")
  if [ "$r" != "no" ]; then
    docker update --restart=no "$c" >/dev/null 2>&1 && echo "  $c: $r -> no"
  fi
done
echo "  --- 仍会自动启动的："
for c in $(docker ps -a --format '{{.Names}}'); do
  r=$(docker inspect -f '{{.HostConfig.RestartPolicy.Name}}' "$c")
  [ "$r" != "no" ] && printf '    %-22s %s\n' "$c" "$r"
done

say "2) SSH 后备公钥（放根卷，/home/albus 挂不上也能登录）"
install -d -m 755 -o root -g root /etc/ssh/authorized_keys
printf '%s\n' 'ssh-ed25519 AAAAC3NzaC1lZDI1NTE5AAAAIJ3DYntdaek78BSw4EUOMHls8YFieWfUbciAHEMmfF9a workbuddy-local-monitor' > /etc/ssh/authorized_keys/albus
chmod 600 /etc/ssh/authorized_keys/albus
chown root:root /etc/ssh/authorized_keys/albus
cp -a /etc/ssh/sshd_config /etc/ssh/sshd_config.bak_w973
LINE='AuthorizedKeysFile .ssh/authorized_keys .ssh/authorized_keys2 /etc/ssh/authorized_keys/%u'
if grep -qE '^[#[:space:]]*AuthorizedKeysFile' /etc/ssh/sshd_config; then
  sed -i "s|^[#[:space:]]*AuthorizedKeysFile.*|$LINE|" /etc/ssh/sshd_config
else
  printf '\n%s\n' "$LINE" >> /etc/ssh/sshd_config
fi
if sshd -t 2>/tmp/sshd_t.err; then
  echo "  sshd -t OK"
  grep -n '^AuthorizedKeysFile' /etc/ssh/sshd_config
  svc=$(systemctl list-unit-files --no-pager 2>/dev/null | awk '/^ssh(d)?\.service/{print $1; exit}')
  echo "  service=${svc:-ssh}"
  systemctl reload "${svc:-ssh}" 2>&1 && echo "  reloaded"
  sshd -T 2>/dev/null | grep -i authorizedkeysfile
else
  echo "  sshd -t 失败，回滚"; cat /tmp/sshd_t.err
  cp -a /etc/ssh/sshd_config.bak_w973 /etc/ssh/sshd_config
fi

say "3) 落盘"
sync
echo "  synced"
