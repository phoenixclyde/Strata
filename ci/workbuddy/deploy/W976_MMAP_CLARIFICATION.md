# W976 "都有人用 mmap"——三个 mmap 的辨析与实测

## 一句话

"人家用 mmap" 说的是 **llama.cpp 默认把 GGUF 整个 mmap**（`use_mmap=true`）。我们引擎里有三处容易混的 mmap，本轮把第三条（PLE 表）从"mmap+锁定"改成"纯 mmap"，**速度不变、释放 26.8 GiB 锁定内存**；而模型专家层照搬 mmap 是实测退步（decode −19%、prefill −60%）。

## 一、三个"mmap"分别是什么

| # | 名字 | 属于 | 含义 | 我们当前 | 引擎默认 | 上游默认 |
|---|---|---|---|---|---|---|
| 1 | GGUF mmap（`use_mmap`） | llama.cpp / 我们的 ggml 层 | 把模型文件映射进地址空间，按页缺页加载 | 用的是我们的 arena（见 #2），文件本身也 mmap 着 | — | **开**（`--no-mmap` 才是全读进 RAM） |
| 2 | `--mmap-experts` | Strata 引擎 | **退出**常驻 expert arena，回到 `MapViewOfFile`（靠 page cache） | **关**（用 arena） | **关**（能装下就用 arena） | 无此概念（上游没有专家分层） |
| 3 | `--ple-io direct\|mmap\|ram` | Strata 引擎 | n-gram/PLE 表的读取方式 | **mmap**（本轮改） | **direct**，RAM 够时自动升级为 `ram` | 无此概念 |

### 第 3 条的关键：`ram` 其实就是 `mmap` + `mlock`

源码 `generate.cpp:5096`：
```cpp
pio.mode = o.ple_io == "mmap" || o.ple_io == "ram" ? PleIo::Mmap : PleIo::Direct;
pio.lock = o.ple_io == "ram";
```
所以三种模式的真实差别只有两点：**是否走 page cache**、**是否锁定**。

## 二、本轮实测（同一台机、同一模型、冷读 `reused=0`）

| 臂 | PLE 模式 | Locked | MemAvailable | decode（warm） | prefill 2.3K |
|---|---|---:|---:|---:|---:|
| A | `ram`（= mmap+mlock） | **26.82 GiB** | 18.8 GiB | 39.5 tok/s | 508 / 551 |
| B | **`mmap`（纯映射）** | **0.00 GiB** | **45.8 GiB** | 37.2 / 39.3 / 40.0 / 42.2（均 39.7） | **545 / 548** |
| C | `direct`（O_DIRECT 逐行） | — | — | 未跑：4K 随机 16 µs/次 × token 路径 | — |

⇒ **B 与 A 等价**（decode 39.7 vs 39.5，prefill 545 vs 529），但 **B 把 26.8 GiB 从"钉死"变成"可回收"**。

`direct` 为什么不做默认：引擎自己的注释（`generate.cpp:5175`）写着
> `--ple-io mmap` was 40-100x faster on some DRAM-less NVMe drives but 7x slower on a SATA SSD (#2040), so it is not chosen for you

我们的盘正是 **DRAM-less + 64 MiB HMB** 的 KIOXIA EXCERIA PLUS G4——按这条经验，`direct` 在本机本来就该被 `mmap` 取代，而 `ram` 只是"顺手锁了"。

## 三、为什么"专家层"不能照搬 mmap

上一轮（W975）实测 `--mmap-experts`：

| | arena | mmap |
|---|---:|---:|
| decode warm | 39.5 | 31.7（−19%） |
| prefill 2.3K | 508/551 | 171/222（−60%） |
| 磁盘读 | 0 | 400 GB |

机理差别：**PLE 表每 token 只取少量行且高度重复（有 1M 行 × 90 B 的行缓存）**，page cache 命中率接近 100%；**专家是 71.7 GiB、按路由随机取**，page cache 顶不住，一缺页就是毫秒级。

## 四、与上游的一致性

llama.cpp 默认 `use_mmap=true` 是因为：它没有专家分层，模型按层顺序访问，OS 页缓存 + 预读足够；而且对超出 RAM 的模型，mmap 是唯一能跑起来的办法。它的 `--no-mmap` 只在"模型装得下 + 想避免缺页"时才用。

我们的引擎在它之上多了一层"专家 arena + VRAM cache"，所以：
- **文件层**：和上游一样 mmap，没变；
- **专家层**：比上游多一个 arena，实测必要（否则 −19%/−60%）；
- **PLE 层**：本轮回归纯 mmap（≈上游行为）。

## 五、本轮改动

```
args += --ple-io mmap           # 35 条
```
效果：`Locked 26.82 GiB → 0`、`MemAvailable 18.8 → 45.8 GiB`、Rss 103 → 75 GiB，**性能不变**。

## 六、建议（按 RAM 松紧分档）

| 情况 | 建议 |
|---|---|
| 现在（RAM 宽松，45.8 GiB 可用） | **`--ple-io mmap`**（已生效）：等价速度 + 可回收 |
| 其他服务要吃内存（ComfyUI 出图等） | 保持 mmap：内核会先回收 PLE 页，属优雅降级；若出现 decode 抖动再退回 `ram` |
| 内存极度紧张、且盘是慢盘 | `ram`（锁 26.8 GiB）——本机不需要 |
| 想要"完全不碰盘" | `ram`，但代价是 26.8 GiB 不可回收 |
| 专家层 | **永远保留 arena**，除非 RAM 装不下模型（那就只能 mmap，且接受 −19%/−60%） |
