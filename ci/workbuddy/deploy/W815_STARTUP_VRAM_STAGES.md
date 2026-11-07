# W815 —— 启动时那个 8.79 GiB 台阶是什么（显存分阶段取证）

> ⚠ **AUDIT11 补注（2026-10-30）三处**
> ①「台阶高度和跳变幅度都能和引擎日志**逐字节对上**」只对 `8.79 + 22.25 = 31.04` 这一句成立；
>   **8.79 内部的分解只有 59% 有来源**（3.535 + 1.063 + 0.63 = **5.23 GiB**），余 **3.56 GiB** 写作"工作区/校验缓冲"、未分解。
> ②「采样 201 点」**不实**：`vram_trace.csv` 实为 **178 个数据行**（覆盖 t=2..201）。三个关键值 8.79@24 / 31.04@197 / 31.41@201 均可复现。
> ③ 本文的「热启 42-46 s」是 **UD-IQ4_XS（arena 55.43 GiB）** 时代的值；
>   换 **UD-Q4_K_XL（arena 71.7 GiB）** 后实测 **165-260 s**（W824 各臂 199/240/231、170/165/196），**该数已失效**。

- 日期：2026-10-27 00:3x-00:5x
- 起因：机主从监控上看显存曲线，发现启动时有一个**停在 8.79 GiB / 32.0 GiB（27.5%）的台阶**，
  且那一段时间**利用率 0%、显存带宽 0%、功耗 16 W**。问这是不是残留。
- 结论：**不是残留，是正常的「权重已上卡、专家缓存还没上卡」的中场**。台阶长度 = **173 s**，
  正好是引擎把 **55.43 GiB 专家竞技场从盘上读进主存**的时间（**0.35 GiB/s**，走页缓存、6 个读线程）。
  台阶高度和跳变幅度都能和引擎日志**逐字节对上**。

---

## 1 逐秒实测（`vram_trace.sh`：1 s 采一次 `/sys/class/drm/card0/device/mem_info_vram_used`）

一次完整的生产重启，逐秒采样直到 `/health` 就绪（`vram_trace.csv` 实为 **178 个数据行**，覆盖 t=2..201 s；
原文写"201 点"是把"覆盖到第 201 秒"当成了点数，AUDIT11 更正）：

| t (s) | 显存 | 日志新增行 | 事件 |
|---:|---:|---|---|
| 2 | 2.96 GiB | 1 | 旧进程正在退出（还没释放完） |
| **3** | **0.01 GiB** | 1 | **归零 = 10.7 MB**（驱动基线） |
| 8 | 0.22 | 11 | 开始载权重 |
| 11-18 | 1.41 → 3.70 | 12 | `499 native projection matrices, 3619.14 MiB of weights` |
| 20-21 | 4.25 → 7.20 | 17-18 | 草稿层载入 |
| **24** | **8.79** | 19 | `mtp: draft layer loaded, 1089 MiB of VRAM` |
| **24 → 197** | **8.79（纹丝不动 173 s）** | 20 → 36 | `expert arena read through the file cache` → `loaded 55.43 GiB at 0.35 GiB/s` |
| **197** | **31.04** | 37 | `expert cache 9873 slots, 22.25 GiB of VRAM` |
| 200 | 31.10 | 44 | `the prompt path borrows 1969 CUDA0 cache slots (4.43 GiB)` |
| 201 | 31.41 | 51 | `668 MiB of VRAM free with everything loaded` ⇒ 就绪 |

**两个数的关系是精确的**：`8.79 + 22.25 = 31.04`，`31.04 + 0.37（verify/借位等）= 31.41`。
所以：

> **8.79 GiB = 「除了专家缓存以外的一切」**（投影矩阵 3619.14 MiB + MTP 草稿层 1089 MiB + HC_Q8 0.63 GiB
> + 工作区/校验缓冲），**22.25 GiB = 专家缓存**，两者之间隔着那 173 s 的盘读。
>
> ⚠ **AUDIT11**：这四项里前三项可加总 = 3.535 + 1.063 + 0.63 = **5.23 GiB（占 59%）**，
> 差的 **3.56 GiB 没有分解依据**，只是被归入"工作区/校验缓冲"。若要闭合这 3.56 GiB，需要用
> `rocm-smi --showmeminfo` 的分配明细或 `HIP` 的 `hipMemGetInfo` 逐段记账 —— **本文没做**，不要当成已解释。

台阶期间 GPU 只等主机，所以监控上正好是：利用率 0%、显存带宽 0%、核心 925 MHz、显存 350 MHz、16 W。
**这不是漏显存，也不是后台还有别的活**——`rocm-smi --showpids` 全程只有引擎一个 KFD 持有者。

---

## 2 为什么这 173 s 是这个数：它是「盘速 × 顺序流」

启动日志（同一台机器，多次一致）：

```
strata generate: expert arena: cudaHostRegister PORTABLE ok; MAP_HUGETLB unavailable
                 (needed 28383 2 MiB pages, vm.nr_hugepages=0); transparent huge pages requested (MADV_HUGEPAGE)
strata generate: expert arena read through the file cache (buffered (not Windows))
strata generate: loaded 55.43 GiB at 0.35 GiB/s
```

- **55.43 GiB ÷ 0.35 GiB/s = 158 s**，与实测台阶 173 s 同量级（差额是开头那段和收尾的重叠）。
- 0.35 GiB/s = **358 MB/s**，是这块 **SATA（Fanxiang S100Pro）**的常态顺序读，不是软件卡住。
- `MAP_HUGETLB unavailable` 是**既存事实**（`vm.nr_hugepages=0`），引擎退到大页（THP）；与台阶无关。

### 2.1 关键结构事实：Linux 上这个载入**走页缓存**，不是 O_DIRECT

源码（`src/core/pinned.cu:827`）：

```cpp
#else
    (void) files; (void) arena_bytes; (void) cache_counts; (void) read_bytes;
    why = "buffered (not Windows)";     // 非 Windows 的默认返回
    return false;
#endif
```

即「文件缓存能不能留住这些专家」这个**探测只有 Windows 有**；Linux 直接返回 false，
日志里那句 `read through the file cache (buffered (not Windows))` 是**标签，不是失败**。
载入本身是 `arena_src.open(o.pack, ..., /*threads=*/6, ...)`：**6 个读线程，经页缓存**。

上游对此有两条 open 的东西：
- **#3624**（open）：给 Linux 加 `O_DIRECT` 分支，由 `STRATA_UNBUFFERED_LOAD=1` 触发。
  该 issue 逐字说本构建这条路径的现状：**"There, `STRATA_UNBUFFERED_LOAD=1` only raises the reader count
  to 16, and the load still runs at the page-cache path's speed."**（他们在 3×NVMe RAID0 上量到
  5.7 GiB/s → 12.0 GiB/s，就绪快 4 s。）
- **#4064/#4065**（open/closed）：冷启动的专家 profile 填充是单线程（某机 8.75 分钟启动里占 336 s）。
  **本机不是这个**：我们 201 s 就绪，且台阶的 173 s 完全由 55.43 GiB ÷ 0.35 GiB/s 解释。

---

## 3 举一反三：这件事直接解释了昨晚 P138 的一半现象

1. **`--ple-io ram` 的表为什么会被挤掉**（W810 的 C 臂，RssFile 986 MB）：
   每次启动都有 **55.43 GiB 的顺序流经页缓存**。26.8 GiB 的表是「刚 touch 过、之后再没人访问」的
   冷文件页，正好是回收器的首选。⇒ **不是 ram 模式本身不好，是这台机器的启动流量必然冲刷页缓存**。
2. **P141 为什么必须「启动前清页缓存」才成立**：清掉之后 `MemFree` 有 63 GB，55.43 GiB 的读放大
   不需要去抢那 26.8 GiB，表才留得住（实测 25.0-26.5 GiB 常驻）。
3. **P141 的 +85 s 启动代价是不可压缩的**：26.8 GiB ÷ 0.35 GiB/s ≈ **77 s**，实测 85 s。
   它和多出来的启动流量是同一笔钱，**换 NVMe 会同时改善启动和 PLE**（见 W810 §8）。
4. **`--vram-reserve-mib 832` 的真实含义**：就绪时 668 MiB 空闲，说明保留量刚好够驱动与临时缓冲，
   没有余量可以再挪——这也解释了为什么调 `--expert-cache` 上限会在就绪前就撞墙。

---

## 4 `STRATA_UNBUFFERED_LOAD=1` 在本机有没有用（实测：**没用，而且我先看错了**）

预期：本构建的 Linux 分支只把 reader 从 6 提到 16，**没有 O_DIRECT**，在 SATA 上不该有收益。

`ab_p45.sh` 交错 P / U 两次启动，读 `loaded 55.43 GiB at X GiB/s` 与就绪秒数：

| 臂 | env | 载入速率 | 就绪 |
|---|---|---:|---:|
| P（生产） | — | 0.27 GiB/s | 242 s |
| U | `STRATA_UNBUFFERED_LOAD=1` | **4.47 GiB/s** | **42 s** |
| **收尾（自动恢复生产，未设该 env）** | — | **3.02 GiB/s** | **46 s** |

**第一眼我把它读成「16.6 倍」——错的。** 第三行是判据：**同一条生产配置、没有任何 env，照样 3.02 GiB/s / 46 s**。
原因是这三行不是同形状：P 冷（页缓存里没有这个 pack），U 与收尾都热（P 刚把 55.43 GiB 读了一遍）。
⇒ **`STRATA_UNBUFFERED_LOAD=1` 在本构建上没有作用**（与上游 #3624 的描述一致：Linux 上它只改 reader 数），
**速度差 100% 来自页缓存**。这条按规则「自比同形状」记在这里，避免下次又把它当成一个旋钮。

### 4.1 由此得到的两档启动（这才是台阶长度的真正变量）

| 启动 | 竞技场载入速率 | 载入耗时 | 总就绪 | 8.79 GiB 台阶持续 |
|---|---:|---:|---:|---:|
| **冷**（pack 不在页缓存） | 0.27-0.40 GiB/s（= 276-410 MB/s，SATA 顺序） | 139-205 s | 201-280 s | **139-205 s** |
| **热**（pack 在页缓存） | 3.0-4.5 GiB/s | 12-18 s | 42-46 s | **12-18 s** |

所以：**机主截图里那条长台阶 = 一次冷启动**；正常情况下只要上一次启动读过这个 pack，重启是 42-46 s、
台阶只有十几秒。（我昨晚在 D 臂中途误执行过一次 `drop_caches`，也正是把后续几次启动推回冷档的原因之一。）

### 4.2 一个绕不开的取舍（RAM 账）

`128.7 GB 总内存 = 引擎 anon 59.7 GB（其中 55.4 GiB 就是专家竞技场）+ PLE 表 26.8 GiB`，剩 ~42 GB。
而「pack 全在页缓存」需要 55.4 GiB ⇒ **两者不能同时全占**：

- **让 pack 常驻页缓存**：重启 46 s，但 PLE 仍按 250 ms/1k 等盘；
- **让 PLE 表常驻**（P141）：提示 -12%，但每次冷启要 200 s+，且 pack 的缓存被挤掉。

这才是 P141 真正的成本结构——不是"多花 3 分钟"这么简单，而是**把 RAM 从"加速启动"挪到"加速提示"**。

---

## 5 数据

- 采样：`/tmp/vram_trace.csv`（**178 行**，1 s，t=2..201），本地副本 `albus/w810/vram_trace.csv`
- 脚本：`albus/r5/vram_trace.sh`（逐秒显存 + 日志行号对齐）、`albus/r5/ab_p45.sh`（P/U 交错）
- 原始件：`data/w815_unbuf_20261027_004539.txt`
- 载入速率序列（同一天，`grep "loaded 55.43 GiB at"`）：0.40 / 0.36 / 0.35 / **0.27** / **4.47** / **3.02** GiB/s

