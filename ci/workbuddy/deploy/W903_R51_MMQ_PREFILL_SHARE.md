# W903 · R51 立据：MMQ 占 prefill 34.6%（最大单项），而我们的 tile 载入仍是标量

> **【更正 2026-11-03 01:3x，`W904`】** §2 把 iacop 的「2x int4 instead of 8x scalar」当成我们的缺口，**这是错的**：
> 我们的 `y_qs` 读取走 `ggml_cuda_memcpy_1<max_cpy>`，HIP 下 `max_cpy = 16` ⇒ **早就是 128-bit**；
> iacop 也只改了 `y_qs`，`x_qs` 的 `get_int_b4` 它同样没动；tile 配置（nwarps=2）也与我们的 GCN 表同量级。
> **§1 的相位数据仍然有效**（gate/up 20.7% + down 14.0% = 34.6%，prefill 最大单项），
> 但真正的瓶颈是**解包 ALU**（dp4a 实测只到峰值的 36%），见 `W904_R51_DP4A_CEILING.md`。


> 2026-11-03 01:3x。**零停服**：数据全部来自生产日志与源码，未跑任何 GPU 实验。

---

## 1 生产实测：prefill 相位分解（7993 tokens，GPU timeline 10,684 ms）

```
gemm gate/up          2210 ms   20.7%
qsa attn              1587      14.9%
gemm down             1491      14.0%
gdn                   1362      12.7%
dequant                604       5.7%
qsa proj               545       5.1%
gdn out proj           518       4.8%
gdn recurrence         451       4.2%
hc read: down+silu     392       3.7%
hc read: up            380       3.6%
router+shared          323       3.0%
hc write 141 / mix 123 / ple 91 / inject 82 / combine 69 / gdn conv+gates 56 / qsa select 51 /
wait copy 45 / qsa norm 43 / host grouping 58 / gather 34 / qsa indexer gemms 22 / embed 3
```

**结论一：prefill 的最大单项是专家 GEMM（MMQ）** —— `gate/up 20.7% + down 14.0% = 34.6%`（3.70 s）。
不是注意力（14.9%），不是 GDN（12.7%）。紧邻的 `dequant 5.7%` 也属于同一条数据通路。

> 同一份日志里另两次（8188 / 7885 tokens）的分布一致：gate/up 20.7–20.8%、down 14.0–14.1%，
> 合计稳定在 **34.6–34.9%**。⇒ 这不是某一次采样的偶然。

## 2 代码事实：我们的 tile 载入是标量

`mmq-load-tiles.cuh:187` 起，`ggml_cuda_mmq_load_tiles_q4_0` 的内层：

```cpp
const block_q4_0 * bxi = (const block_q4_0 *) x + kbx0 + i*stride + kbx;
const int qs0 = get_int_b2(bxi->qs, kqsx);      // ← 一次 32-bit
x_qs[i*(MMQ_TILE_NE_K + 1) + txi] = qs0;
```

每线程每行每块只取 **一个 int（4 B）**。整个 overlay 目录（1645 行 `mmq.cuh` + 1770 行
`mmq-load-tiles.cuh`）里 **`int4` / `float4` / `__ldg` 出现 0 次**。

对照 `iacopPBK/llama.cpp-gfx906` 的 `ggml/src/ggml-cuda/gfx906/matmul/mmq.cuh`，文件第 3 行逐字写着：

```
// MMQ vectorized loads: 2x int4 (128-bit) instead of 8x scalar loads
```

实现是 `const int4 vec0 = *((const int4 *) &y_qs[base_addr]); const int4 vec1 = *((const int4 *) &y_qs[base_addr + qi]);`

**结论二：差距是结构性的，不是“换个指令”** —— 它把每线程的载入从 8 次 4 B 变成 2 次 16 B
（同时改了 tile 的线程映射），这正是我们缺的那一层。

## 3 为什么现在值得做

- W897 实测：`STRATA_PREFILL_MMQ=0`（退回 FP16/rocBLAS）⇒ prefill **8.975 → 14.079 s（1.57×）**。
  也就是说 MMQ 路径已经在工作，**但没人量过它自己离屋顶多远**。
- 它是 prefill 的 **34.6%**，而 prefill 是当前唯一还有大空间的面（decode 已在地板，W895）。
- 载入是标量 ⇒ 每 16 B 的块数据要 4 条 32-bit 指令，地址运算与 LDS 事务数都翻倍。

## 4 判据（写死，避免又一次“换了指令但没收益”）

1. **只认 prefill TTFT**（同 prompt、≥4 rep、中位、`|Δ| ≥ 2×CV`）；
2. **输出必须一致**：同 prompt 贪心前 64 token 的 argmax 序列相同（不比文本哈希——引擎 run 间不确定，见 W899 §7.11）；
3. **decode 只守不劣化**（MMQ 不参与 decode，但共享 `strata_kq` 的初始化）；
4. 若载入改造后 <2×CV，按 DONE_NEG 关闭，不再做第二轮微调。

## 5 下一相的具体落点

- 目标文件：`ggml-tq-overlay/mmq-load-tiles.cuh`（`q4_0 / q4_1 / q5_0 / q5_1 / q8_0` 五个 loader）
  与 `mmq.cuh` 的 `mmq_get_dp4a_tile_x_sizes` 布局；
- 先做**一个** type（q4_0）做 A/B，证明 `|Δ| ≥ 2×CV` 再推广；
- 复用本次的“换对象重链”通路：只重编 `strata_kq` 与相关 TU，四分钟出二进制；
- **不碰** `STRATA_PREFILL_MMQ` 的默认值，不改生产配置。
