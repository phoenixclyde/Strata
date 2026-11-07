# W789 R5（HC `TILEV` 实验）裁定：路径 A 源码级无效，路径 B 是唯一出路

> 补 `AUDIT7 P2-6` 的留档缺口：R5 是本轮唯一改变过生产配置的动作（切 `0.2.4r5`、回滚），此前只有 `P96` 一行 + 日志。
> 本文把实验、违规、回滚、以及**源码级反证**收在一处。判据全部可复核。

---

## 1 动机（来自 `W788`）

`W788` 实测 M 档 97 窗口稳态：HC 四组投影合计 **7.42 ms/window（占 16.1%）**，而 Q8 权重的纯读取地板是 **0.78 ms**（48 层 x 4 矩阵 x 3.28 MB = 629 MB，@805 GB/s）。差 **9.5 倍**。

`W788 §3` 把它归因为：`DOWN_BLOCKS = LR/WARPS = 320/8 = 40`（+1 inject = **41 blocks**），而 MI50 有 **60 CU** -> 19 个 CU 空转；再加 shared 34 KB -> 1 block/CU。于是提了两条路径：

- 路径 A（最小）：`TILEV` 2560 -> 1280，shared 34 KB -> 17 KB，"3 blocks/CU"
- 路径 B（完整）：借 routeK `dense_gemv` 的 `RPT/KCHUNK` 做 K 切分 + reduce，块数 400

## 2 做了什么

`deploy/docker/patch_gr_tilev.py`（fail-closed，7 项自证）：把 `fused_gr.cu:1078` 里 gfx906 硬编码的 `const bool small_tile = false;` 改成 `STRATA_GR_TILEV` 门控 —— 不设 = 2560（与 0.2.4 逐字节同路径），`=1280` 走小 tile。1280 的内核实例化与 `tv==1280` 分支本来就在源码里（`:1307-1310`），不需要新写内核。

构建 `strata-gfx906:0.2.4r5`：`[160/160]` RC=0，二进制 `0a77b236c78de832…` / 34,771,968 B（比 0.2.4 多 400 B），`tilev_marks: 2`、`final_checkpoint: 0`（R1 补丁已移出）、Q6K=OFF。

## 3 实际发生了什么（含违规）

| 时间 | 动作 | 问题 |
|---|---|---|
| 05:5x | 切生产到 `0.2.4r5`，跑臂 A（`tilev=2560`，3 runs） | **A/B 未跑完就切了生产**（违反 06:0x 才立的纪律⑧） |
| 06:0x | 臂 A 数据：`62.72`（预热）/ `53.17` / `53.02` ms/window | 对照用的"基线 51.58"没有任何留档出处 |
| 06:0x | 臂 B（`tilev=1280`）**从未运行** | 无任何效果结论 |
| 06:0x | 回滚到 `0.2.4` | 干净（容器 Created 未变、33 args 原样、config md5 与 05:51 一致） |

**事后补上的验证**（本该在切换前做）：臂 A 就是"默认路径"，它的 `decode GPU stages` 行里 `hc0 down + hc1 down` = `1.33+0.44=1.77` 与 `1.37+0.46=1.83`，基线是 `1.33+0.45=1.78` —— **镜像的默认路径与 0.2.4 一致**，没有回归。这一点当时没验，是流程缺陷，不是数据缺陷。

## 4 裁定：路径 A 无效（源码级，三条独立理由）

### 理由一：块数不变，而块数才是缺的那个量

`fused_gr.cu:42`：`constexpr int DOWN_BLOCKS = LR / WARPS;  // 40 blocks of 8 rows; one more for the inject rows`

`TILEV` 不参与块数计算。grid 恒为 **41**，CU 有 **60**。**块数比 CU 少，调度器每个 CU 最多分到 1 块**，此时把 shared 从 34 KB 降到 17 KB，不会有第二块落到同一个 CU —— 减小 shared 只在"块数 > CU"时才能提高每 SM 块数。

### 理由二：小 tile 的唯一收益条件在我们的 T 上不成立

小 tile 的作用是让"8 个 token 装进一次 launch"。实测容量公式（`fused_gr.cu:1133-1134`）：

```
capacity = usable / (tv * sizeof(float))     usable = 64 KiB opt-in
chunk    = min(capacity, kFusedGrMaxT=8)
```

| tv | capacity | chunk |
|---|---|---|
| 2560 | 65536 / 10240 = 6 | **6** |
| 1280 | 65536 / 5120 = 12 | **8** |

日志 `avg T = 3.33-3.47` -> **两种 tile 下都只有一次 launch**。小 tile 省不到任何一次 launch。

### 理由三：预取深度直接减半

`TQ = TILEV / 8 / 32`：2560 -> **10**，1280 -> **5**（`:307`，每 lane 每 tile 在飞的 `uint4` 权重块）。在占用率只有 6.8%、靠 ILP 撑吞吐的内核里把 MLP 减半，方向是**负的**。

### 附带：`W788` 的占用率本身要改

gfx906 `Wavefront Size: 64`、`Max Work-item Per CU: 2560`（= 40 wavefront/CU）。256 线程 = **4 个 wavefront**（32-lane 分组共用 wavefront），不是 8 个。所以每 CU 占用 **10%**、聚合 **6.8%**，不是 20% / 13.6%。详见 `AUDIT7 P1-2`。

## 5 路径 B（唯一该做的动作）

要治"19 个 CU 空转"，只能**加块数**。三个方向，按改动量排：

| 方向 | 做法 | 块数 | 代价 |
|---|---|---|---|
| **B1** | K 切分：每块只算 `D/KSPLIT`，再加 reduce | 41 x KSPLIT（KSPLIT=2 -> 82，=4 -> 164） | 需要一个 reduce 内核（`lo[T][LR]` 很小，一次 `hc` 归约即可） |
| **B2** | 行切细：每块 4 行而不是 8 行（改 `warp -> row` 映射） | 80 (+1) | 改动在内核主体，风险中 |
| **B3** | 块内 K 并行：512 线程、8 行、K 分两半 | 41（但每块 8 wavefront） | 仍是 41 块，只提高每 CU 的 wavefront 数（10% -> 20%） |

**判据（发车前写死）**：`decode GPU stages` 行的 `hc0 down + hc1 down` 之和（基线 `1.77-1.83`）降 >= 25%，且 `hc0 up + hc1 up` 不劣化，且 >=3 runs 交错、governor 前后一致。**总 `ms/window` 只作参考**（它受 spec 接受率影响，run 间离散 50.76-53.87，约 ±3%，判不了 3% 级的差异）。

## 6 现在的状态

- 生产：`strata166-407` = `strata-gfx906:0.2.4` / `0.1.49.2` / slots 9901 / env 4 项 / governor 44 核 `schedutil`
- 实验件留档**勿用**：镜像 `0.2.4r5`、`0.2.4r1`；容器 `strata166-407.r5`、`strata166-407.r1`
- 回滚位：容器 `strata166-407.bak024`、`bak023`、`bak022b`；镜像 `0.2.4` / `0.2.3` / `0.2.2b`
- `P96` 已改判 REJECTED（源码级反证，**未实测**）；若将来要实测路径 B，应先在 8091 临时容器上做，不碰生产
