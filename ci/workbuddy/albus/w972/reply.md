**搬完了，也校验完了：`/models` 408 GB 逐字节一致；`/home/albus` 152 GB / 98 万文件，内容差异 0。** 中途我犯两个错，都修好了，下面直说。

## 一、生产容器（8 字段）

| # | 项 | 值 |
|---|---|---|
| 1 | 容器 / 镜像 | `4f387a12e84b` / `strata-gfx906:0.2.10-101`（image `5267df6dbdeb`） |
| 2 | 运行中引擎 | `209d8f50a77d9d45803c9cbbe3e70dde`，44,908,992 B（0.8.0 构建） |
| 3 | **config** | md5 `07b4cedd70534ffb23b07f09df8882ae`；exe=`/data/bin/strata-0.1.56-080`；**args 33 条**；**env 9 条**（未改） |
| 3a | args 明细 | `--pack /data/packs/ud-q4_k_xl` `--native …UD-Q4_K_XL-00001-of-00004.gguf` `--expert-profile /src/data/expert-profile.bin` `--expert-cache auto` `--pcie-frac 0.20` `--spec 4` `--spec-min-p 0.70` `--mtp /data/mtp/rt` `--max-context 262144` `--kv k8v4` `--prefill auto:16384` `--prompt-cache-every 8192` `--expert-profile-save /data/profiles/q4kxl-learned.bin` `--conversation-cache-mib 4096` `--vision` `--mtp-window 8192` `--vram-reserve-mib 832` |
| 3b | env 明细 | `HSA_OVERRIDE_GFX_VERSION=9.0.6` `STRATA_PREFILL_CPU_SHARE=auto` `STRATA_PREFILL_CPU_SHARE_MAX=3072` `STRATA_RESIDENT_HEADROOM_GIB=0.5` `STRATA_ROCBLAS_TUNING=/data/gfx906-rocblas-5.7.0.txt` `STRATA_GFX906_TUNED=1` `STRATA_CKPT_MOVE_PARK=1` `STRATA_DECODE_TIMING=1` `STRATA_SPEC_DEPTH=1` |
| 4 | 健康 | `/health` status=ok、`loaded:true`、restarts=0、StartedAt `2026-11-04T15:24:40Z`；真实请求 2,354 tok / 4,493 ms = **524 tok/s** |
| 5 | 资源隔离 | `ulimit -l = unlimited`；引擎进程 `VmLck 28,125,140 kB` |
| 6 | 显存布局 | `expert cache 7463 slots / 21.79 GiB`、`borrows 2606 (7.62 GiB)`、`767 MiB of VRAM free` |
| 7 | 回滚件 | 引擎 `strata-0.1.56`（`ae085365…`）；`cp /data/strata-huihui-ud-iq4_xs.json.bak_w970 …json`；fstab 备份 `/etc/fstab.bak_w972`；`ci/strata-ci rollback --exe strata-0.1.56 --apply` |
| 8 | 本轮改动 | **存储迁移**：`/home/albus` + `/models` → NVMe；disk = build = running 三方一致（`209d8f50…`）；根卷 220G → **773G free** |

## 二、主线

`gfx906/mi50 @ 304bd3be` · tag `mi50-0.2.10-r31` · 上游 `ffa80d73` · 落后 0 / 领先 41 · 工作树脏 0 行。

## 三、本次落生产

停机窗口 **23:22–23:27（约 5 分钟）**：停全部容器 → 增量同步 → 瞬时覆盖挂载 → 起容器；**重启 5 次**（全部容器一次停/起，strata 含其中）。其余时间（bulk 22:44–23:21、校验 23:27–00:08）生产正常服务。

## 四、进度 + 队列

**176 条 / 已结 102（58.0%）**；主线 148 / 102 / 68.9%；死块池 0/28。
队列：**六长度档 A/B（新盘）** → 摘 `#29953` 越界 padding → R88-量 → R86-A/B → R87 → R46 → R91。

---

## 一、你的两个问题，正面回答

**1）"容器不应该都停掉吗？"——对，切换时我停了全部**（`docker stop $(docker ps -q)`），因为校验需要一个冻结的基准。**但我随后用 `docker start $(docker ps -aq)` 起回来，把 6 个历史实验容器也拉起来了** —— 它们抢 8090、还改了构建目录。这是我的错，已处理：全部 `--restart=no` 且保持 exited。

**2）"务必确认复制完全一致"——用内容校验，不是看大小：**

| 树 | 结果 |
|---|---|
| `/models`（408 GB） | **5 行差异**：2 个目录 mtime + ComfyUI 的 `.log/.prev.log` 在重启时**轮转互换**（7,834 ↔ 8,661 字节一一对应）⇒ 数据**逐字节一致** |
| `/home/albus`（152 GB，984,046 文件） | **226 行差异**：139 只差 mtime；**49 个内容不同，全是构建产物/日志/缓存** |

那 49 个的来历查清了：新副本 mtime 全在 **23:24–23:26**，正是我误启历史构建容器的时间——它们重跑、重建 `.o`、把 `_build.log` 从 2,027,746 截成 401 字节。处置：从**冻结快照**（根卷只读视图）恢复 45 个，**复验剩余差异 = 0**；唯一没恢复的是生产日志（切换后正常增长，新副本更大）。

## 二、文件系统：4Kn + xfs，理由

`nvme0n1` → **4Kn 化**（`flbas=0x1`，PHY/LOG 均 4096）→ GPT 单分区 → **xfs `-m reflink=1,bigtime=1 -n ftype=1`，挂载 `noatime`**：

- xfs：与根卷同工具链、大文件顺序读最优、元数据开销小；
- 不选 btrfs：压缩对已量化 GGUF 无收益，而这块盘是 **HMB（无独立 DRAM）**，随机写敏感；
- 不选 zfs：ARC 会跟 77 GB 模型的页缓存抢内存；
- 4Kn：减少小写入的读改写；TRIM 由系统 `fstrim.timer` 负责。

## 三、布局：路径不变，容器零改配置

```
UUID=22a2f408-…  /nvme          xfs  defaults,noatime,nofail
/nvme/home_albus /home/albus    none bind,nofail,x-systemd.requires-mounts-for=/nvme
/nvme/models     /models        none bind,nofail,x-systemd.requires-mounts-for=/nvme
```
`findmnt --verify` 通过。三个依赖容器（strata 2 处、comfyui 11 处、searxng 1 个文件）只重启，未改挂载参数。

## 四、我犯的第二个错（已修）

`umount /mnt/old_home /mnt/old_models` 时**共享传播**把 `/models` 一起卸了。当场发现并 `mount --bind --make-private /nvme/models /models` 恢复，容器内外均已核对。教训：本机 bind 互操作一律 `--make-private`。

## 五、现状

- 根卷 935G，用 163G，**空 773G**（旧数据 553 GB 已删）；新盘 1.9T，用 596G，**空 1.3T**；
- 生产：health ok，524 tok/s —— **与迁移前同量级**，说明冷读瓶颈不在盘（专家流式/内存），下一步六长度档 A/B 再定位；
- **没动** `/var/lib/docker`（仍在根卷）、没改根卷、没重启机器（fstab 已静态验证，下次开机生效）。
