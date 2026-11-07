# 166 开机后核对清单（W973，2026-11-05）

> 重启目的：清掉 `/mnt/old_*` 叠加残留挂载，验证 fstab bind + docker 启动顺序。

## 一、30 秒内先看三件事

```bash
# 1) 两个 bind 是否自动建好（关键：挂不上则 SSH/容器全废）
for p in /nvme /home/albus /models; do printf '%-12s ' $p; findmnt -no SOURCE,FSTYPE $p || echo MISSING; done

# 2) 残留是否已随重启消失
findmnt -R /mnt/old_home /mnt/old_models 2>/dev/null || echo "残留已清"

# 3) 容器是否只有 6 个自启
docker ps --format '{{.Names}} {{.Status}}'
```

预期：三个路径全部 `nvme0n1p1 xfs`；`/mnt/old_*` 不存在；容器只有
`strata166-407`、`searxng`、`netdata`、`open-webui`、`comfyui-cu130`、`portainer`。

## 二、生产（装载约 4 分钟）

```bash
for i in $(seq 1 60); do r=$(curl -s -m 3 localhost:8090/health || true); case "$r" in *'"loaded": true'*) echo UP; break;; esac; sleep 5; done
docker exec strata166-407 md5sum /data/bin/strata-0.1.56-080   # 应 209d8f50a77d9d45803c9cbbe3e70dde
docker exec strata166-407 df -hT /data /models | tail -2      # 应 nvme0n1p1
```

## 三、若 `/home/albus` 没挂上（SSH 仍可用，因为已经有根卷后备钥匙）

```bash
sudo mount --bind /nvme/home_albus /home/albus
sudo mount --bind /nvme/models /models
```
后备公钥位置：`/etc/ssh/authorized_keys/albus`（根卷，644 root:root）；
`sshd_config` 已含 `AuthorizedKeysFile .ssh/authorized_keys .ssh/authorized_keys2 /etc/ssh/authorized_keys/%u`。

## 四、已知改动（本次重启前做的）

| 项 | 内容 |
|---|---|
| 宿主 `/data` | 已删（空壳，无引用） |
| docker | `/etc/systemd/system/docker.service.d/10-mounts.conf`：`RequiresMountsFor=/nvme /home/albus /models` |
| 容器自启 | 14 个历史实验容器改为 `restart=no` |
| SSH | 增加根卷后备公钥路径 |
| 文件系统 | `/nvme` xfs 4Kn，挂 `defaults,noatime,nofail` |
| fstab 备份 | `/etc/fstab.bak_w972`；`sshd_config.bak_w973` |
