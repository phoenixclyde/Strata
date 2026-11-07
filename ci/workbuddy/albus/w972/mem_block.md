## W972 · NVMe 迁移完成（2026-11-04 22:40 → 11-05 00:2x）

- 新盘：KIOXIA EXCERIA PLUS G4 2TB，`nvme0n1`，**切成 4Kn**（`flbas=0x1`，PHY/LOG 4096），GPT + 单分区。
- FS：**xfs**（`-m reflink=1,bigtime=1 -n ftype=1`，挂载 `noatime`）。理由：与根卷一致、大文件顺序读最优、元数据写少；
  不选 btrfs（压缩对已量化模型无收益 + HMB 盘随机写敏感）、不选 zfs（ARC 与 77 GB 模型抢内存）。
- 迁移：`/home/albus` 152G + `/models` 408G = **560G**，bulk（限速 350 MB/s）+ 停机 delta；**路径不变**（bind 到同一路径），
  容器只重启不改配置（strata 2 处、comfyui 11 处、searxng 1 个文件）。
- fstab：`UUID=22a2f408-… /nvme xfs defaults,noatime,nofail` + 两条 bind（`x-systemd.requires-mounts-for=/nvme`）；`findmnt --verify` 通过。
- 旧数据已删：根卷 **220G → 773G free**（+553G）。
- **校验**：`/models` 只 5 行（2 个目录 mtime + comfyui 日志轮转，字节数一一对应）；`/home/albus` 226 行里 137 只差 mtime、
  45 内容不同是**我误启动历史构建容器**造成的（23:24–23:26 重建 .o/截断日志），已从冻结快照恢复并复验 **0 差异**。
- **两个我犯的错**：① `docker start $(docker ps -aq)` 把 6 个历史实验容器拉起（抢 8090/显存、改构建目录）⇒ 已停 + `--restart=no`；
  ② `umount /mnt/old_home /mnt/old_models` 因**共享传播**把 `/models` 一起卸了 ⇒ 已 `mount --bind --make-private` 恢复。
  **教训：本机 bind 挂载互操作必须 `--make-private`；切换容器只能 `docker start <白名单>`。**
- 迁移后性能：冷读 2354 token = **4493 ms / 524 tok/s**（与迁移前同量级，说明冷读瓶颈不在盘而在专家流式/内存）。
