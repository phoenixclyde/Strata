
### 9.25 v37 顶栏全项核账 + 内存全量口径 + 整机功耗 + 双 SSD（2026-11-05）

机主交办：顶栏每一项按实际核实 / 内存条不是全部内存 / 要整机功耗 / 两块盘要看读写温度寿命。
**结论先行**：只有一处是「判据错」，其余都是「口径不全」。

- **[判据错] 常驻生产服务被报「显存泄漏」**：v36 的 `STRATA_SERVE=$(ps ... | grep -F "strata --serve")` 只认字面形态；
  生产容器跑的是 `/data/bin/strata-0.1.56-090 --serve`（带版本后缀）=> 漏检 => 探针判 IDLE + ratio 3093x => 红灯假警。
  已放宽为 `strata[A-Za-z0-9._-]* --serve`，并新增 `prod_srv`（`serve/server.py --engine strata`）；页面**只归因不改判**
  （判决文案「显存有主·生产服务」warn / ratio 与 KFD 挂 defer / 状态格 IDLE+服务）。探针 56 令牌与 rc 一字未动。
- **[口径] 内存**：netdata `system.ram` 只有 4 维（free/used/cached/buffers），缺 MemAvailable / Unevictable；
  页面原来 `used/(used+free+cached+buffers)` 与 `free` 的 used 对不上。改读 `/proc/meminfo` 全量，
  **三段自洽**：已用 = `total-available`（= free 3.3.17+ 的 used）、可回收 = `available-free`、空闲 = `free`。
  [!] 踩过一次：把整个 `Cached` 当第二段 => 与 mlocked(Unevictable) 重复计数、条被 100% 截断。
  本机实测 Cached 43.9GiB 里约 26.8GiB 是 mlocked => MemAvailable 只有 16GiB（不是 free+cache）。**判据必须能加满分母**。
- **[能力边界] 整机功耗**：X99-CH8 无 BMC（无 `/dev/ipmi*`、ipmitool 未装）=> **墙插功耗软件不可测**。
  只能给 RAPL package + RAPL dram + 双卡 四项实测合计（是下界），标题必须写明「不含主板/盘/风扇/电源损耗」。
- **[能力边界] SSD 寿命**：本机 netdata **没有** NVMe/SMART 采集器（contexts 里 0 个），只有 hwmon 温度与 disk.io 读写。
  寿命/已写入/通电只能容器内 `smartctl`。两个前置条件各踩一次：
  1) `--device /dev/nvme0 /dev/nvme0n1 /dev/sda`（device cgroup；nsenter 不切 cgroup，宿主管里看得见也没用）；
  2) **CAP_SYS_RAWIO**：SATA 的 SMART 走 SG_IO，缺它报 `Read Device Identity failed: Operation not permitted`
     （NVMe 走 NVME_IOCTL_ADMIN_CMD，只需已有的 SYS_ADMIN）。缺任一个都**不报错**，只是那几格静默 `--`。
  判据补进 `recreate` 自证 4/5 与 `verify` 的 `health_mem / health_ssd_temp / health_ssd_life / dev_block / health_prod_srv`。
- **健康 ≠ 寿命**（查证 NVMe 规范 + smartmontools）：`Percentage Used` 是厂商估算的已耗耐久度，100 也不代表故障；
  真信号是 Critical Warning 非 0 / Available Spare 低于该盘自报阈值 / Media Errors。故加了 SMART 徽章。
- **SATA 的「已写入」不显示数字**：属性 241 的单位随厂商而异（32MiB / LBA / 1GiB 都有），本盘不在 smartctl 库内 => 不猜。
- 部署链未变（push assets -> build_image -> recreate -> verify）。新增三个设备的自证写进 recreate，避免下次重建静默丢。
