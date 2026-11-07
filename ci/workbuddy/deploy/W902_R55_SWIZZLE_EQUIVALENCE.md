# W902 · R55 第一相：`ds_bpermute` 换 `ds_swizzle` —— 逐位等价已证，微基准 3.14×

> 2026-11-03 01:2x。**零停服**：只编译/运行三个探针（各 1 block 或 2400 block 的独立二进制），
> 生产容器与二进制未动。工作目录 `/home/albus/strata166/tmp`，源码留 `albus/w902/`。

---

## 1 结论先行

1. **LLVM 不会自动用 DPP**：一个 32-lane 蝶形（offset 16/8/4/2/1）编出来是 **5 条 `ds_bpermute_b32`**，
   `v_mov_dpp` = 0、`ds_swizzle` = 0。
2. **这 5 条交换不便宜**：与等量 FMA 链相比，含归约的核慢 **2.74×**（0.2049 vs 0.0745 ms）。
3. **`ds_swizzle_b32` 与 `__shfl_xor(v,n,32)` 是同一置换**（n=1/2/4/8/16 全 0 失配，含 wave64 高半组），
   而速度快 **3.14×**（0.2046 → 0.0652 ms）。⇒ R55 的技术前提成立，且**天然逐位相同**。
4. **坑**：手写 `asm("ds_swizzle_b32 … offset:%2")` 的立即数编码**是错的**（实测 0x081F/0x101F 都退化成 xor-1，
   0x401F 甚至变成恒等）。必须用 `__builtin_amdgcn_ds_swizzle`。

---

## 2 证据一：ISA（`isa_probe.cu`）

```
$ clang++ -x hip -O3 --offload-arch=gfx906 --cuda-device-only -S isa_probe.cu
ds_bpermute = 5      v_mov_dpp = 0      ds_swizzle = 0      permlane = 0
```

同一个 kernel 里的“等量算术但不交换”版本编出 5 条 `v_fma_f32`，没有 LDS 相关指令。

## 3 证据二：交换的成本（`shfl_cost.cu`，2400 block × 256 线程 × 64 rep）

| 版本 | 耗时 | 比值 |
|---|---:|---:|
| 蝶形（5×`ds_bpermute` + 5 add） | **0.2049 / 0.2051 ms** | 2.74× |
| 同形（5×fma，无交换） | 0.0745 / 0.0745 ms | 1.00 |

两次重复一致（±0.1%）。

## 4 证据三：`ds_swizzle` 的置换与宽度（`swz_builtin.cu`，1 block 64 线程）

BitMode 编码（[AMD GCN 交叉通道指令文档](https://gpuopen.com/learn/amd-gcn-assembly-cross-lane-operations/)）：
`lane_out = (lane & and_mask) | or_mask ^ xor_mask`，swap-n 即 `(n << 10) | 0x1F`：

| pattern | lane0..7 读到 | lane32..35 读到 | 对应 `__shfl_xor(...,32)` | 失配 |
|---|---|---|---|---:|
| `0x041F` (n=1) | 1 0 3 2 5 4 7 6 | 33 32 35 34 | 同 | **0** |
| `0x081F` (n=2) | 2 3 0 1 6 7 4 5 | 34 35 32 33 | 同 | **0** |
| `0x101F` (n=4) | 4 5 6 7 0 1 2 3 | 36 37 38 39 | 同 | **0** |
| `0x201F` (n=8) | 8 9 10 11 12 13 14 15 | 40 41 42 43 | 同 | **0** |
| `0x401F` (n=16) | 16 17 18 19 20 21 22 23 | 48 49 50 51 | 同 | **0** |

**关键**：高半组（lane32..）取的是**本组**的 lane，不跨 32 组 —— 与 `strata_hip.h` 的 LOGICAL 32-lane 契约一致（W901）。

## 5 证据四：速度（`swz_test.cu`，同形状）

```
value mismatches over 64 lanes: 0  => SAME permutation
butterfly shfl 0.2046 ms   swizzle 0.0652 ms   68.1% faster   (3.14×)
```

---

## 6 可落地的改法（下一相）

现在 `strata_hip.h` 把 `__shfl_xor_sync(mask, v, n, ...)` 映射成 `__shfl_xor(v, n, STRATA_SHFL_W(...))`，
默认宽度 32。**在宽度为 32 且 `n ∈ {1,2,4,8,16}` 时改用 `__builtin_amdgcn_ds_swizzle`**，语义不变、逐位相同。

两条路线：

| 路线 | 做法 | 代价 | 风险 |
|---|---|---|---|
| **A（推荐）** | 垫片里加 `strata_shfl_xor32(v, n)`：`switch (n)` 五个 case 各用立即数 pattern，其余回落 `__shfl_xor` | 每处交换多一个 5 路分支（编译器常把常量实参折掉） | 低；失败只影响性能 |
| B | 逐个热点站点改成模板（`qsa_select` 39 处、`qsa_prompt_attn` 24、`iq_kernels` 22、`dflash2` 21、`sampler` 20） | 改动面大、易漏 | 中 |

**判据（不变）**：①逐位相同（本件已证置换相同，仍需整核 parity）；②独立探针 `|Δ| ≥ 2×CV`；
③VGPR/占用不退化。**注意**：3.14× 是**纯交换链**的加速，整核收益 = 交换占比 × 3.14，
所以下一相必须先量“目标核里归约占多少”，否则会高估。

**先量谁**：`qsa_select` 的 `block_topk_wide_kernel`（39 处默认宽度归约、每元素 5 步扫描）与
`sampler`（20 处）——两者都在 decode 的关键路径上，且都不是带宽受限。

---

## 7 复现

```bash
cd /home/albus/strata166/tmp
CXX=/opt/rocm/llvm/bin/clang++ ; F='-x hip -O3 --offload-arch=gfx906'
$CXX $F --cuda-device-only -S isa_probe.cu -o isa_probe.s && grep -c ds_bpermute isa_probe.s
$CXX $F shfl_cost.cu   -o shfl_cost   && HSA_OVERRIDE_GFX_VERSION=9.0.6 ./shfl_cost
$CXX $F swz_builtin.cu -o swz_builtin && HSA_OVERRIDE_GFX_VERSION=9.0.6 ./swz_builtin
$CXX $F swz_test.cu    -o swz_test    && HSA_OVERRIDE_GFX_VERSION=9.0.6 ./swz_test
```

---

## 8 第二相：真核实测 —— **无收益**（R55 关闭）

在分支 `exp/R55-swizzle`（worktree `work/r55`，基线 `d963c791`）把 `qsa_select.cu` 的 32-lane XOR 归约
整体改到 `ds_swizzle`（TU 内 `#undef/define __shfl_xor_sync`，其它文件不动），编译后：

| 版本 | `ds_bpermute` | `ds_swizzle` |
|---|---:|---:|
| 基线 | **258** | 32 |
| swizzle | **69（−73%）** | 221 |

然后用公开入口 `qsa_block_topk` 建独立探针（`albus/w902/topk_bench.cpp`，几何取 `qsa_real_shapes()`，
基线/改版各自链接一次，`ids` 与 `qsa_block_topk_ref` 逐项比对）：

| 上下文 | 基线 ms/call | swizzle ms/call | 差 | ids |
|---|---:|---:|---:|---|
| 32K（n_bid 8192） | **0.0500** | 0.0498 | −0.4% | 2051/2051 全等 |
| 131K（n_bid 32768） | **0.1629** | 0.1635 | +0.4% | 全等 |
| 262K（n_bid 65536） | **0.2518** | 0.2520 | +0.1% | 全等 |

**结论**：指令构成确实翻转了（−73% bpermute），但**时间不动** ⇒ 这个核不是交换受限的，
它由 4 趟基数选择的标量/共享内存工作主导。微基准那 3.14× 只对“纯交换链”成立，**不能外推**。

**R55 = DONE_NEG**。保留：①分支 `exp/R55-swizzle` 的改动是**逐位等价**的（ids 三档全等），
将来若出现真正归约受限的核可直接取用；②教训写死：**先量占比，再谈指令替换**。

**下一步别再走这里**：`sampler` 的 20 处、`qsa_prompt_attn` 的 24 处与 `qsa_select` 同属“混合型”，
在没有占比证据前不再尝试。
