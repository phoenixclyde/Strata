# W975 NVMe 之后的三层数据策略（VRAM / RAM / DISK）

## 结论

**NVMe 不该用来替换 RAM。** 实测：把 71.7 GiB 的 expert arena 换成 mmap（靠 page cache + NVMe）后，内存省下 72 GiB、启动快 20 s，但 **decode −19%、prefill −60%、磁盘被重读 400 GB**。生产保持原分层，只改了内核侧 I/O 策略，换来 **加载速度 +9%**。

## 一、硬件实测（nvme0n1，1.9 TiB，PCIe 3.0 x4）

| 模式 | 结果 |
|---|---|
| O_DIRECT 顺序（8 GiB） | **2.4 GB/s** |
| buffered 顺序（8 GiB，部分命中） | 6.1 GB/s |
| 4 KiB 随机 O_DIRECT | 253 MB/s（≈16 µs/次） |
| 旧盘（Fanxiang SATA） | ≈0.5 GB/s |

内存 128 GB（131.8 GB），显存 34.34 GB（已用 33.69 GB）。

## 二、当前三层实际构成（来自启动日志 + smaps）

| 层 | 内容 | 大小 | 性质 |
|---|---|---:|---|
| VRAM | expert cache | **21.79 GiB / 7463 slots** | GPU 命中即可计算（R4 hit path） |
| VRAM | KV（k8v4, 262144 ctx）+ dense + MTP draft | 余量 | — |
| RAM | **expert arena** | **71.73 GiB** | 匿名页，`cudaHostRegister` 部分 pinned（Locked 26.8 GiB） |
| RAM | **PLE 表** | **26.8 GiB** | `--ple-io ram` 自动选中，mlock 锁定 |
| DISK | GGUF 分片 | 114 GB | 只用于填充；稳态 **0 MiB** 读取 |

**稳态验证**：2,353 token 与 59,053 token 两次冷读，`/sys/block/nvme0n1/stat` 读扇区增量 **0**——推理热路径完全不碰盘。

## 三、已生效的改动（内核侧，无停机）

`/etc/sysctl.d/99-strata-nvme.conf`
```
vm.swappiness = 10            # arena 是 71.7 GiB 匿名页，换出即灾难
vm.vfs_cache_pressure = 50
vm.dirty_background_bytes = 268435456
vm.dirty_bytes = 1073741824   # 读多写少，避免大 RAM 上的 20% 回写尖峰
```
`/etc/udev/rules.d/60-nvme-readahead.rules`
```
ACTION=="add|change", KERNEL=="nvme0n1", ATTR{queue/read_ahead_kb}="2048"
```
效果：**arena 加载 2.95 → 3.21 GiB/s（+9%）**，重启等待 50 s。

## 四、被数据否掉的改动

### 4.1 `--mmap-experts`（放弃 arena，用 page cache + NVMe）

| 指标 | arena（现役） | mmap |
|---|---:|---:|
| MemAvailable | 19.8 GiB | **91.9 GiB** |
| 启动到 health | ~50 s | **30 s** |
| decode（warm） | 39.5 tok/s | **31.7**（−19%） |
| prefill 2.3K | 508 / 551 tok/s | **171 / 222**（−60%） |
| 磁盘读 | 0 | **400 GB**（838.9M sectors） |

机理：`prefill plan inputs: ... 0.0 GiB RAM copy (0 lend slots kept), file tier 49.9 GiB`——每层专家都要从映射/盘上取，page cache 命中率跟不上解码节奏；引擎注释里 34 GB 机器上 `71.97 vs 34.78 ms/token` 的结论在 128 GB + NVMe 上**依然成立**。

### 4.2 `--ple-io direct`（省 26.8 GiB）

未跑完（见 §5 事故）。判据：4 KiB 随机 16 µs/次，PLE 行 90 B、每层多行、位于 token 路径；引擎默认 `direct`，但驻留策略在 RAM 充足时自动升级为 `ram`，说明作者也认为这条路径不该碰盘。**留作 RAM 紧张时的备选，不作为默认。**

## 五、本轮两次操作事故（都已恢复）

1. **配置 `env` 是 dict，我按 list 改写** → wrapper `AttributeError: 'list' object has no attribute 'items'`，容器重启循环，生产中断约 4 分钟；用 `.bak_w974` 恢复 dict 后正常。
   教训：改 JSON 前先打印 `type()`；`json.load` 后不要假设容器类型。
2. **`pkill -f <脚本名>` 匹配到自己的 SSH 命令行** → 会话被杀（两次）。
   教训：远端清理进程用 `pgrep -f` 先看 PID，且模式不要出现在自己的命令行里。

## 六、政策决定

| 层 | 策略 | 依据 |
|---|---|---|
| VRAM | 保持 auto（7463 slots / 21.79 GiB），不缩 KV 换缓存 | 剩余仅 740 MB，KV 缩水是能力损失 |
| RAM | 保持 arena 71.7 GiB + PLE 26.8 GiB | mmap 实测 −19%/−60% |
| DISK | 2 MB 预读 + swappiness 10 + none 调度器 | 加载 +9%，防换出 |
| 未来 | 若 RAM 吃紧（ComfyUI 等）：先用 `--ram-keep-gib` 限 arena，再考虑 `--ple-io direct`，两者都有本轮量化的代价 | — |

## 七、当前生产状态

`exe=/data/bin/strata-0.1.56-090`（`eea5ea37…`）、args 33、env dict 9、config md5 `172693a4…`、
`expert cache 7463 slots / 21.79 GiB`、MemAvailable 18.8 GiB、health ok、`restart=0`。
