# 关机前状态（2026-11-04 22:0x，为加 NVMe 而关机）

## 关机前事实
- 生产容器 `strata166-407`：`restart=unless-stopped`，**没有手动 stop**，所以开机后 Docker 会自动拉起（其余 searxng/netdata/open-webui/comfyui/portainer 同）。
- 引擎：`/data/bin/strata-0.1.56-080`（llama.cpp **0.8.0**，md5 `209d8f50a77d9d45803c9cbbe3e70dde`）；config md5 `07b4cedd70534ffb23b07f09df8882ae`。
- 回滚件：`/data/bin/strata-0.1.56`（md5 `ae085365…`）+ `strata-huihui-ud-iq4_xs.json.bak_w970`。
- 磁盘：**只有一块** `sda` 953.9G（Fanxiang S100Pro）→ LVM：swap 16G + root 934.8G（xfs，77% 用，剩 220G）。
  `/models`（77 GB+）与 `/data` **都在根卷上**，不是独立挂载。
- `fstab` 只有 swap / root(xfs) / boot(ext4) / efi —— 加盘不影响启动。
- Docker Root：`/var/lib/docker`（overlay2，也在根卷）。

## 开机后要做（按顺序）

1. `docker ps` 看 `strata166-407` 是否自己起来了；没有就 `docker start strata166-407`。
2. 等 health：`curl -s localhost:8090/health`（装载约 4 分钟，看到 `"loaded": true` 才算好）。
3. 确认引擎没变：`docker exec strata166-407 md5sum /data/bin/strata-0.1.56-080` 应为 `209d8f50a77d9d45803c9cbbe3e70dde`。
4. 新盘：`lsblk` 应出现 `nvme0n1`。
   - 建议：`sudo mkfs.xfs -f /dev/nvme0n1`（整盘，不分区；若要与根卷一致就 xfs）
   - 挂到 `/models`：先把现有 `/models` 内容搬过去（77 GB+），再写 fstab：
     `UUID=<新盘UUID> /models xfs defaults,noatime 0 2`
   - **搬之前**先停容器，搬完 `docker start`。
5. 搬完验证：`df -h /models` 应显示新盘；起服务后看 `prompt N tokens ... tok/s` 是否改善（这是本轮 prefill 的唯一物理瓶颈候选）。

## 已知的优化线索（等盘到位后做）
- 冷读模型 `t ≈ 1.7 s + n/822`，短 prompt 只到 ~525 tok/s；专家竞技场是 `through the file cache (buffered)`。
  换到 NVMe 并让竞技场常驻，是当前最可能把短档拉起来的物理手段。
