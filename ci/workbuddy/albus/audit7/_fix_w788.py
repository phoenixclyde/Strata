import io

p = 'D:/workbuddy_space/strata_ws/deploy/W788_HC_ATTRIBUTION.md'
s = io.open(p, encoding='utf-8').read()

# 1) §3 占用率表：wave64 更正
old_tbl = """| 量 | 值 | 后果 |
|---|---|---|
| grid | **41 blocks** | MI50 有 **60 CU** => 19 个 CU **完全空闲**（68% 覆盖） |
| shared | 3.33 × 2560 × 4 B ≈ **34 KB** | 每 CU 64 KB => **1 block/CU** |
| warps/CU | 256 线程 = **8 warps** | MI50 容量 40 warps => **20% 占用** |
| 合起来 | 68% × 20% ≈ **13.6%** | 与 9.5 倍差同量级 |

**这就是根因。** `W785 §2.2` 已经排除了"寄存器溢出"（实际在跑的 `gr_down_multi_kernel<2560,8,true>` 是 114 VGPR / priv=0），本轮把第二个可能也排除了：**不是带宽、不是溢出，是 block 数不足 + shared 太大挤掉 occupancy。**

源码自己的注释也承认这条路（`:301`）：

> `smaller tiles raise how many blocks share an SM (the 41-block grid)`"""

new_tbl = """| 量 | 值 | 后果 |
|---|---|---|
| grid | **41 blocks** | GPU 有 **60 CU**（`rocminfo` 实测）=> 19 个 CU **完全空闲**（68% 覆盖） |
| shared | 3.33 × 2560 × 4 B ≈ **34 KB** | 每 CU 64 KB => **1 block/CU** |
| wavefront/CU | 256 线程 = **4 个 wavefront** | 每 CU 容量 **40 wavefront**（`Max Work-item Per CU 2560 / 64`）=> **10% 占用** |
| 合起来 | 68% × 10% ≈ **6.8%** | 1/0.068 = 14.7 倍，与实测 9.5 倍同量级 |

> **[2026-10-25 06:3x `AUDIT7 P1-2` 更正]** 原表按 CUDA 语义算成 `8 warps` / `20%` / `13.6%`，**错 2 倍**。
> gfx906 的 `Wavefront Size: 64`（`rocminfo` 实测），256 线程 = 4 个 wavefront；内核虽按 32 lane 分组
> （`:310` `warp = t >> 5`），但**两个 32-lane 组共用一个 wavefront**，所以只占 4 个 wavefront 槽。
> 数值更正后，9.5 倍与 14.7 倍（纯占用率预期）之间还差一截 => 占用率不是**唯一**损失源。

**根因要分开说，这一点原文混在一起了：**

- **主因是 block 数**：41 < 60 CU，19 个 CU 空转（68% 覆盖）。
- **shared 在这里不是约束**：它只决定"每个 SM 能放几块"，而**我们只有 41 块，比 CU 还少**，每 CU 本来就最多 1 块。
  所以 `:301` 那句 `smaller tiles raise how many blocks share an SM` 描述的是"块数 > CU"的场景，**在我们这里不成立**。
  这个区分直接决定路径 A 该不该做，见 §5。

`W785 §2.2` 已经排除了"寄存器溢出"（实际在跑的 `gr_down_multi_kernel<2560,8,true>` 是 114 VGPR / priv=0），
本轮把第二个可能也排除了：**不是带宽、不是溢出。**"""

assert s.count(old_tbl) == 1, s.count(old_tbl)
s = s.replace(old_tbl, new_tbl, 1)

# 2) §5 路径 A 标为源码级无效
old_a = """### 路径 A（最小验证，改 1 个模板实参）
`TILEV` 从 2560 降到 **1280**：shared 34 KB -> 17 KB，每 CU 可从 1 block 升到 3 blocks。
风险：`TILEV` 在注释里只用于 sm_75（64 KiB 卡的切片），gfx906 上是否等价未验证；`TQ = TILEV/8/32` 会从 10 变 5，每 lane 少读一半。
判据：`hc0 down` 阶段 ms 降 >= 20%，且 decode 输出与改动前一致。"""

new_a = """### 路径 A（最小验证，改 1 个模板实参）—— **[已判无效，不要做]**

> **[2026-10-25 06:3x `AUDIT7 P1-3` 源码级判定：此路径结构上不可能有效。R5 已按此路径做了一半，裁定见 `W789_R5_TILEV_VERDICT.md`。]**
>
> 1. **块数不变**：`DOWN_BLOCKS = LR/WARPS` 与 `TILEV` 无关，grid 恒 41；而 CU 有 60。
>    **块数比 CU 少时，减小 shared 不会有第二块落到同一 CU** —— 占用率一点都不会变。
> 2. **小 tile 的唯一收益条件不成立**：它省的是"8 token 装进一次 launch"。实测 `chunk = 64KiB/(tv*4)`：
>    `tv=2560 -> 6`、`tv=1280 -> 8`；而我们的 `avg T = 3.33-3.47`，**两种 tile 下都只有一次 launch**。
> 3. **预取深度减半**：`TQ = TILEV/8/32` 从 10 降到 5，每 lane 在飞的权重块减半，方向是负的。
>
> 原文写的"每 CU 可从 1 block 升到 3 blocks"是本路径的核心假设，而它在 41 < 60 时不成立。

原方案（供留档）：`TILEV` 2560 -> 1280，shared 34 KB -> 17 KB；风险是 `TQ` 从 10 变 5。"""

assert s.count(old_a) == 1, s.count(old_a)
s = s.replace(old_a, new_a, 1)

# 3) §5 路径 B 升为唯一路径
old_b = "### 路径 B（完整方案，参考 routeK 的 KCHUNK）"
new_b = "### 路径 B（**唯一有效路径**，参考 routeK 的 KCHUNK）—— 治的是 block 数"
assert s.count(old_b) == 1
s = s.replace(old_b, new_b, 1)

# 4) §2 小计与地板一致性
old_sum = "| 小计 | 3.10 | 2.61 | 0.88 | 0.88 | **7.47** |"
new_sum = "| 小计 | 3.10 | 2.61 | 0.88 | 0.88 | **7.42**（列相加 7.47，与 `P91` 的 HC 组取 7.42，差 0.7% 为舍入） |"
assert s.count(old_sum) == 1
s = s.replace(old_sum, new_sum, 1)

io.open(p, 'w', encoding='utf-8', newline='\n').write(s)
print('W788 patched: 4 items')
