## 2026-11-04 22:0x · 166 关机（加 NVMe）

- 关机前清单：容器全 `unless-stopped`/`always`（**没有手动 stop**）⇒ 开机 Docker 自动拉起；无 ninja/cmake 在跑；`sync` 已做。
- 磁盘只有一块 `sda` 953.9G（Fanxiang S100Pro）→ LVM swap16G + root 934.8G(xfs, 77%)；**`/models` 与 `/data` 都在根卷**，非独立挂载；fstab 干净。
- 引擎：`/data/bin/strata-0.1.56-080`（0.8.0，md5 `209d8f50…`），config md5 `07b4cedd…`；回滚件 `strata-0.1.56`（`ae085365…`）+ `.bak_w970`。
- 关机命令：`sudo systemctl poweroff --no-block`（已确认 SSH 断、ping 超时）。
- 开机清单落在 **`~/strata166/POSTBOOT_NVME.md`**（也在工作区 `deploy/POSTBOOT_NVME_20261104.md`）：
  ① `docker ps` 看 strata166-407 是否自起；② `curl localhost:8090/health` 等 `loaded:true`（约 4 min）；
  ③ 核引擎 md5；④ `lsblk` 看 `nvme0n1`，建议 `mkfs.xfs` + 搬 `/models` + fstab（`noatime`）。
- 目的：把 77 GB+ 的 `/models` 挪到 NVMe。当前专家竞技场是 "through the file cache (buffered)"，
  冷读模型 `t≈1.7s+n/822`、短档仅 ~525 tok/s，**I/O 是最可能的物理瓶颈**。
