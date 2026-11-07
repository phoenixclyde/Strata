# W945 · 源码级评估：mx-llama.cpp 的 Q5_1 repack 到底是什么（逐行对照我们的 Q5_1 装载）

> **【AUDIT24 P1 · 2026-11-04】§6.1 的 PMC 必须标形状**：**0.36% / 0.11%** 是
> **16 专家 × 320 token**（生产形状）测的；同一支 `kq_bench` 在 **16 × 1024** 上复测，Q4_K 的
> `MemUnitStalled` = **9.1–9.6%**（`AUDIT24`，CSV 留 `data/w952pmc/`）——大 M 时访存停滞升 **27 倍**。
> ⇒「MMQ 完全不是访存受限」**只在生产形状成立**，引用必须带形状。
> 结论（repack 收益不能按 +84% 外推、必须单内核 A/B）不变。

- 日期：2026-11-04 15:0x–15:3x
- 源码：`mxxm-t/mx-llama.cpp` @ master，`ggml/src/ggml-cuda/q8_repack/`（8 个文件，190 KB）已下到 `~/strata166/ref/mx/`
- 对照对象：我们的 `~/strata166/llama.cpp`（`ggml-cuda/mmq-load-tiles.cuh:393`、`vecdotq.cuh:206`）+ `src/prefill/moe_mmq_tab.cuh`
- 一句话：**repack 不改一个数值，只把 24 B 交错的 `block_q5_1` 拆成三个平面**；它解决的问题是**我们的 down 每一次 16 B 读都从 `24*i + 8` 开始**（8 字节错位），而不是指令数。

---

## 1 布局的源码定义（`repack-common.cuh`）

```c
// Q5_1: de-aliased nibble rows, a 4-byte fifth-bit plane and a half2 {d, m} plane per 32-value block: canonical 6 bpw.
case GGML_TYPE_Q5_1:
    return (size_t) ne1 * ((size_t) repack_qs_stride(ne0 / 2) + (size_t)(ne0 / 32) * 8);
```

其中

```c
template <typename T> static inline T repack_qs_stride(const T ne0) {
    T rs = ne0;
    if (rs % 128 == 0) { rs += 16; }      // 行首避开 HBM channel stride，保持 uint4 对齐
    return rs;
}
```

⇒ 每个 32 值 block 仍然是 **24 B**（16 nibble + 4 第五位 + 4 half2{d,m}），**显存零增长**；只是把三类数据**分平面连续存放**。

## 2 为什么这个类型是"给我们准备的"（源码注释原文）

```c
template <> struct rp_traits<GGML_TYPE_Q5_1> {
    // The 32-value affine block: x = d*q + m, q in [0,31], one half2 {d, m} per block, no super-block.
    // Quantizers fall back to it whenever a row is not a multiple of 256, so it is the type the K-quants
    // cannot cover (the 640-column expert downs of Qwen3.8).
```

**"the 640-column expert downs of Qwen3.8"** —— 我们的 down 就是 `[2560, 640]`（640 列不是 256 的倍数 ⇒ 量化器回退到 Q5_1）。
这不是巧合，是它做这个 trait 的原因。

## 3 读法对比：同样 8 条位运算，差在**地址**

### 3.1 我们现在（`mmq-load-tiles.cuh:415-434`）

```c
const block_q5_1 * bxi = (const block_q5_1 *) x + kbx0 + i*stride + kbx;   // 块步进 24 B
const int ql = get_int_b4(bxi->qs, kqsx);        // qs 在块内偏移 8（d2+m2+qh4 之后）
const int qh = get_int_b4(bxi->qh, 0) >> (4 * kqsx);
int qs0 = (ql >>  0) & 0x0F0F0F0F;
qs0 |= (qh << 4) & 0x00000010;  ... 4 条
int qs1 = (ql >>  4) & 0x0F0F0F0F;
qs1 |= (qh >> 12) & 0x00000010; ... 4 条
```

`block_q5_1` 的字段顺序是 `{half2 dm; uint8 qh[4]; uint8 qs[16];}` ⇒ **`bxi->qs` 的地址 = 24·i + 8**。
每一次 16 B 读都**不是 16 B 对齐**：跨 128 B cache line 时走两次事务，且同一 warp 内不同行（i 不同）的地址间隔 24·stride（我们的 down stride=1 行，⇒ 480 B）——**没有任何合并规律**。

### 3.2 mx 的 repacked 读法（`repack-common.cuh` 的 `rp_traits<Q5_1>::load_w`）

```c
const uint4  pk = rp_ldcs_u4(qsp + (size_t) wrow * g.rs_u4 + sb);          // 16 B 对齐，一次拿整块 nibble
const uint32_t h = *reinterpret_cast<const uint32_t *>(wbase + g.hoff + wi * 4);   // 第五位：连续平面
for (int j = 0; j < 4; j++) {
    plo[j] = (pq[j] & 0x0F0F0F0Fu)        | (rp_spread1((h >> (4 * j))      & 0xFu) << 4);
    phi[j] = ((pq[j] >> 4) & 0x0F0F0F0Fu) | (rp_spread1((h >> (16 + 4 * j)) & 0xFu) << 4);
}
d = *reinterpret_cast<const uint32_t *>(wbase + g.doff + wi * 4);          // half2{d,m}：连续平面
```

- **指令数完全相同**（4+4 条展开 + 两次标量读）；
- 差的只有：①`qs` **16 B 对齐**；②`qh`、`dm` 各自在**连续平面**里，`wi = row*n_sub + sb` 让相邻 block 的同一字段相邻 ⇒ warp 内地址**线性**，可以合并；
- `rp_ldcs_u4` 还带 **.cs（streaming）缓存提示** —— 权重只用一次，不该污染 L2。

⇒ **收益全部来自访存，不来自算术**。这也解释了为什么 FEATURES 表里 Q5_1（6 bpw、最碎的格式）拿到 +84%，而 Q4_K（4.5 bpw、块更大）只有 +2~5%。

## 4 数值：逐字节相同（这是最大的优点）

`repack_q51_host`（`repack-common.cu:285`）全文只有 15 行，三个 `memcpy`：

```c
for (int64_t row = 0; row < ne1; row++)
  for (int64_t sb = 0; sb < n_sub; sb++) {
      const block_q5_1 * b = &blocks[row * n_sub + sb];
      const size_t wi = (size_t) row * n_sub + sb;
      memcpy(dst + row * qs_str + sb * 16, b->qs, 16);
      memcpy(dst + hoff + wi * 4, b->qh, 4);
      memcpy(dst + doff + wi * 4, &b->dm, 4);
  }
```

**没有一个 bit 被改动** ⇒ 与 FEATURES 的「Q5_1: byte-identical output on 1 GPU」一致。
⇒ 与 dot8 / int8 attention 不同，**repack 不需要 KL 门**（只需一次输出比对确认）。

## 5 移植到我们路径：改两处 + 一个 stride

我们的专家路径不经过 ggml tensor（`moe_mmq_tab.cuh` 直接给 16 个专家指针），所以**不搬它的 buffer-type 框架**，只搬三样：

| # | 改动 | 位置 | 规模 |
|---|---|---|---|
| 1 | **host repack 函数**（Q5_1 版，逐字节照抄 15 行） | 新增 `src/prefill/repack_q51.*` | ~40 行 |
| 2 | **expert stride**：`expert_bytes = 1,228,800`（canonical）→ `repack_gcn_nbytes(Q5_1,640,2560)`（repacked，同值 1,228,800，因为 320 % 128 ≠ 0 无 bump） | `moe_mmq_tab.cuh` 的 `p.expert_bytes` / `launch_mul_mat_q_tab` | 3 行 |
| 3 | **`ggml_cuda_mmq_load_tiles_q5_1` 的取数**：把 `bxi->qs/qh/dm` 换成三平面索引 | `mmq-load-tiles.cuh:415`（qs/qh 循环）+ 第二个循环的 `dm` | ~40 行，加 `#if STRATA_Q51_REPACK` |

**注意**：`expert_bytes` 数值不变（都是 1.23 MB），所以 `moe_mmq_tab` 的步进**不用改**；但**内部偏移**全变了（`qs` 不再在 +8），所以第 3 项必须与第 1 项同时上，否则读到垃圾。

**加载时机**：我们是按需上传（prefill 每 chunk 借 2606 槽 / 7.62 GiB）。
两种做法：①上传后跑一次 repack kernel（GPU 内读 1.23 MB + 写 1.23 MB，按 1 TB/s 约 2.5 µs/专家，可忽略）；②在 host 侧 PLE 内存里 repack 再传（多一次主机内存搬运，不划算）。
⇒ 选 ①，并在专家槽的生命周期内只做一次（槽复用时按 expert id 判断）。

## 6 本机实测：对齐假设成立，但"访存不是瓶颈"—— 收益必须实测，不能按 +84% 外推

### 6.1 PMC（停服独占，`rocprofv3 --pmc VALUBusy MemUnitStalled FetchSize`）

| kernel | VALUBusy | **MemUnitStalled** | 时间 |
|---|---:|---:|---:|
| `mul_mat_q<(ggml_type)7, 64, false>`（Q5_1 down） | **58.0%** | **0.36%** | 6.29 ms / 4 launch（=1.57 ms） |
| `mul_mat_q<(ggml_type)12, 64, false>`（Q4_K gate/up） | **60.6%** | **0.11%** | 10.14 ms |

⇒ **MMQ 完全不是访存受限**（memory-unit stall 不到半个百分点），是 VALU 受限。所以 repack **不可能靠"少等内存"拿到 +84%**；它只能靠**少发 load 指令**。

### 6.2 ISA（同一个自建二进制，`mul_mat_q<(ggml_type)7, 64, false>`，1,301 条指令）

| 指令 | 条数 |
|---|---:|
| **`global_load_dword`（32-bit）** | **29** |
| `global_load_dwordx2` / `dwordx4`（64/128-bit） | **0 / 0** |
| `ds_read2_b32` | 80 |
| `v_dot4_i32_i8` | 256 |
| `v_and_b32` + `v_lshlrev_b32` + `v_or3_b32`（第五位展开） | 86 + 53 + 32 |

**canonical 的权重载入是 29 次 32-bit 读，一条 128-bit 都没有** —— 对齐假设在**指令层**成立（`bxi->qs` 落在 24·i+8，编译器不敢发 `dwordx4`）。repack 后同类读取应是 ~8 条 `dwordx4`（带 `.cs`），**省 ~21 条静态 load**。

但 21/1301 = 1.6% 的静态指令，动态还要看循环展开与执行次数；**外证的 +84% 是在 dense 27B（大 M、权重复用高）上测的，我们的 MoE 每专家只有 ~320 token**，同一份权重的摊薄倍数差一个量级。

### 6.3 结论与判据（下调预期）

| 口径 | 值 | 说明 |
|---|---|---|
| 外证 Q5_1 dense +84% | **不能直接搬** | 形状（M）与基线（他们替代整套 ggml MMQ）都不同 |
| 外证本模型四卡 +11% | **可信度较高** | 同模型、43 个 Q5_1 tensor，但那是四卡 tensor split |
| 本机 down 占 prefill | 13.8% | `W927` |
| **本机端到端预期** | **未知，区间 0 ~ −6.3%** | 必须做单内核 A/B 才能定 |

**唯一能判的实验**：`kq_bench` 两臂（canonical / repacked），同形状 `[2560,640]`、16 专家 × 320 token、停服独占、≥5 rep。
判据：**Δ ≥ 40% 才动生产路径**；<20% 判否；20–40% 记为"边际"，与 R46 对比后再定。

## 7 与上一轮的关系（为什么要推翻"只剩 attention"）

- `W942` 的 VALUBusy **67.1%** 说的是"VALU 忙"，而 Q5_1 的 VALU 时间里有一大块正是**为不整齐的 24 B 结构做地址/拆分**（我们整 kernel 的 `v_add_u32`+`v_mul_lo_u32`+进位链 = 19.7%，`W943`）；
- repack 不改指令种类，只让**同样的指令**少做无用功（对齐 + 合并）——这是 Q5_1 上唯一还能拿的一档，也是外证唯一在**本模型**上给出端到端数字的一档。

## 8 已核对、明确不搬的部分

| mx 的东西 | 为什么不搬 |
|---|---|
| `buffer.cu` 的 repack buffer-type + view cache | 我们不经过 ggml tensor，专家是裸指针 |
| `mul-mat-id.cu` 的 tile prefix-sum / tile_meta | 我们的 `moe_mmq_tab` 已有 16 专家指针表 + `ids_dst`，功能重叠 |
| `mul-mat.cu` 的 dense 路径 | 我们 dense 走 rocBLAS/自研 GEMV，不经 ggml |
| `MMQ_RP_Q8_MOE_MMV_MAX_TOKENS` 等调参 | 属 GEMM 调度层，我们的 J=64/stream_k=false 已由 PMC 判过（R60/R63） |
