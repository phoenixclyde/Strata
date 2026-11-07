# W904 · R51 重定题：不是「载入不够宽」，是「解包 ALU 吃掉 dp4a」

> **【更正 2026-11-03 03:0x，`W908 §5`】** §2 把 dp4a 实测上限写成 **19.07 TMAC/s**，这是我那支探针
> 只用了 4 个累加器的结果。同卡第三方（skyne98 wiki-gfx906，ILP4）测到 **21.7–22.3 TMAC/s**，
> 理论 26.5 ⇒ 真上限比 19.07 高约 12–17%。**方向不变**（我们离墙更远），但"36%/24%"这类百分比要按 21.7 重算：
> MMQ 形状 6.90 TMAC/s = 上限的 **32%**（原写 36%），生产反推 4.55 TMAC/s = **21%**。


> 2026-11-03 01:3x。零停服：只跑了一支微基准（`albus/w903/dp4a_ceiling.cu`），未改生产。
> 本件同时**更正 `W903 §2`**：那段把 iacop 的「2x int4 instead of 8x scalar」当成我们的缺口，
> 实际上我们早就是 128-bit 了。

---

## 1 先撤回一个错误前提（W903 §2）

`W903 §2` 写「我们的 tile 载入是标量，iacop 是 128-bit」。逐行核对后：

| 位置 | 我们（overlay） | 结论 |
|---|---|---|
| `y_qs`（激活 Q8_1）的读取 | `mmq-vec-dot.cuh:44-47` → `ggml_cuda_memcpy_1<max_cpy>`，而 `common.cuh:399-409` 在 `GGML_USE_HIP` 下 `max_cpy = **16**` | **已是 128-bit** |
| `x_qs`（权重）tile 载入 | `mmq-load-tiles.cuh:745` → `get_int_b4(bxi->qs, txi)`，每线程每行 4 B | 标量，但 **iacop 也没改这里** |
| iacop 到底改了什么 | `gfx906/matmul/mmq.cuh:3` 的注释指 `y_qs`：`const int4 vec0 = *((const int4*)&y_qs[base_addr])` | **只改 y_qs，且上游后来已用 `memcpy_1<16>` 覆盖** |
| tile 配置 | iacop `gfx906-config.h` 只定义 `GFX906_MMQ_NWARPS 2` 与一个 Q8 cache；tile 形状仍走通用表 | 与我们的 `mmq-config-gcn.cuh`（Q4_K: 256 threads / nwarps 2 / I 64-128 / J 8-64）**同量级** |

⇒ **「移植 iacop 的向量化载入」没有实质内容可移**。R51 若按原题做，就是第二个 R55。

## 2 重新定位：MMQ 的 dp4a 效率只有 36%

微基准（`albus/w903/dp4a_ceiling.cu`，60 CU、4 block/CU、256 线程、5 次重复）：

| 版本 | 吞吐 | 说明 |
|---|---:|---|
| 纯 dp4a（寄存器，无访存） | **19.07 TMAC/s**（38.1 TFLOPS-eq） | 本卡 dp4a 实测上限（理论 26.5，达成 72%） |
| **MMQ 形状**（1 次 LDS 4B + 解包 + 4×dp4a） | **6.90 TMAC/s** | **= 纯 dp4a 的 36%** |
| LDS 读带宽 | 6293 GB/s | 该循环只用到 1723 GB/s（**27%**）⇒ 不是 LDS 瓶颈 |

**指令账**（`vecdotq.cuh:533-556` 的 `vec_dot_q4_K_q8_1_impl_mmq`）：

```
每个 dp4a 前都要 (v[j] >> 4*i) & 0x0F0F0F0F —— 1 移位 + 1 与
⇒ 16 个 dp4a 要配 32 条 ALU ⇒ 48 条指令做 64 个 MAC = 1.33 MAC/指令
⇒ 相对纯 dp4a 的 4 MAC/指令 = 33%      实测 36% ✔ 机制吻合
```

**所以瓶颈是解包 ALU，不是载入，也不是 LDS。**

## 3 真正的杠杆：把解包从行循环里提出来

`mmq-vec-dot.cuh` 的循环嵌套是：

```cpp
for k01:                     // K 方向的分块
  for j0 (step nwarps):      // y 的每一行
    for i0 (step warp_size): // x 的每一行
      u[] = y[j] 的 4 个 int
      sum[..] += vec_dot(x[i], u, ...)   // ← 在这里面对 x[i] 做 32 条解包
```

固定 `i` 时，`x[i]` 的解包被**重复了 J/nwarps 次**（J 取 8…64 ⇒ 4…32 次）。交换 j/i：

```cpp
for k01:
  for i0 (step warp_size):
    unpack x[i] 一次 -> xv[16]
    for j0 (step nwarps):
      u[] = y[j] 的 4 个 int
      sum[..] += dot_pre(xv, u, ...)     // 只有 16 条 dp4a + 4 条载入
```

- 每个 (k01,i,j) 的指令数：**54 → 21**（−61%），理论上限 ~2.6×；
- 累加口径不变：每个 `sum[j,i]` 槽在每组 k01 里仍然只加一次，**逐位相同**（不改求和顺序）；
- 寄存器代价：`xv[16]` ints（+16 VGPR），需要复核不越占用率预算。

## 4 判据（沿用 W903，不放松）

1. **只认 prefill TTFT**（≥4 rep、中位、`|Δ| ≥ 2×CV`）；
2. 输出一致：同 prompt 贪心前 64 token 的 **argmax 序列相同**；
3. decode 只守不劣化（MMQ 不参与 decode）；
4. **先只改 Q4_K 一个 type**（gate/up = prefill 的 20.7%），过门再谈 Q5_1（down 14.0%）；
5. 不过门即 DONE_NEG，不再第二轮微调。

## 5 复现

```bash
# 本机已放 /home/albus/strata166/tmp/dp4a_ceiling.cu
/opt/rocm/llvm/bin/clang++ -x hip -O3 --offload-arch=gfx906 dp4a_ceiling.cu -o dp4a_ceiling
HSA_OVERRIDE_GFX_VERSION=9.0.6 ./dp4a_ceiling
```

## 6 一处测量保留意见（写下来避免被误用）

我加的第 4 个核（解包提升 + 8 行复用）测出的绝对数**超过纯 dp4a 峰值**，说明该核的 MAC 计数或代码生成
不可信（编译器可能消除了部分工作），**故本件不引用它的绝对值**，只把它当作「机制方向正确」的旁证。
真正的判定只能来自真实内核的 prefill TTFT。

---

## 7 实施与 A/B：解包 hoist **实测变慢 6–10%**，假设被推翻

### 7.1 改了什么（最小面）

只改 Q4_K 一个实例，且**不碰 vendored 源码**：

| 步 | 做法 |
|---|---|
| 补丁目标 | `mmq-vec-dot.cuh` 的 `ggml_cuda_mmq_vec_dot_q4_K_q8_1_dp4a` + `vecdotq.cuh` 新增 `..._impl_mmq_pre` |
| 载体 | **`ggml-cuda` 的完整副本**（`work/r51-gc`），补丁打在这份副本上；pinned llama.cpp 与构建树都不动 |
| 为什么必须整目录复制 | 实例 TU 是 `#include "../mmq.cuh"`（相对它自己的目录）⇒ 只用 `-I` 指 overlay **无效**。第一版就踩了这个坑：编出来的对象与基线**同大小 973,544 B**，说明编的是未打补丁的代码 |
| 重编范围 | 只有 `mmq-instance-q4_k.cu` 一个 TU（Q4_K 的内核实例在它里面，`moe_mmq.cu` 只调用不实例化） |
| 换库与链接 | `ar r libstrata_mmq.a mmq-instance-q4_k.cu.o` → `ninja -t commands strata` 的链接行 → 新引擎 40,747,184 B |
| 生效证据 | 对象 **973,544 → 948,712 B（−24,832）**，且 md5 变化 ⇒ 解包代码确实被削掉 |

### 7.2 资源占用（`-Rpass-analysis=kernel-resource-usage`）

| 模板实例 | 基线 VGPR / 占用 | hoist VGPR / 占用 |
|---|---|---|
| `J=8` | 61 / 4 波·SIMD | 63 / 4 |
| `J=16` | 117 / **2** | 80 / **3** |
| `J=24` | 86 / 2 | 64 / **4** |

**没有 VGPR 溢出**（`VGPRs Spill: 0`），占用率反而变好。所以「变慢是因为溢出」这个猜测不成立。

### 7.3 A/B（同一 prompt、同 env，只差引擎二进制；服务端日志口径）

| 臂 | prompt | prefill | tok/s |
|---|---|---:|---:|
| **A 基线** `strata-0.1.55t` | 6440 | **8936 ms** | **720.7** |
| A 基线 | 6462 | 8933 ms | 723.4 |
| **B hoist** `strata-r51` | 6440 | **9449 / 9676 ms** | **681.0 / 665.6** |
| B hoist | 6462 | 9468 / 9726 ms | 682.0 / 664.4 |

⇒ **−6% ~ −10%，方向一致、不是噪声**（A 两条的 tok/s 差 0.4%，B 内部 2.4%）。

> 口径纠正：`ci/bench_pair.py` 这次报了 `PREFILL 19.425 s / 0 prompt tokens`，那是它把一个 prompt 的
> 两次请求（一次 cancelled、一次真跑）叠算了。**以服务端 `strata serve: prompt ... read in` 为准**。

### 7.4 为什么假设错了（这条比结果更重要）

微基准的「MMQ 形状」只含 `1×LDS + 解包 + 4×dp4a`，而真实 `vec_dot` 每次调用还带：
`y_ds` 的 half2 载入 + `__half22float2`、`sc[i]`/`m[i]` 的字节载入、3 次 float 乘加。
这些是**每次 (i,j) 都付**的固定成本，量级不亚于 32 条解包。

而且基线里 `x_qs` 是 `const int * __restrict__`、`j0` 循环 `#pragma unroll` —— LLVM 很可能**已经把这
32 条解包 CSE 到循环外**了。若是这样，我的改动只是把编译器已经做好的事用手写了一遍，还额外拉长了
`xv[16]` 的生存期、改变了访存顺序（y 变成内层广播读）⇒ 净效果为负。

**教训（写死）**：微基准必须包含被调函数的**完整固定成本**，否则「36% 的峰值」这种结论不能外推到真实核；
R55 也是同一个错误（纯交换链 3.14× → 真实核 0%）。**连续两次**，说明这是方法问题，不是运气问题。

## 8 判定

**R51 = DONE_NEG（本变体）**，生产已恢复（`strata166-407`，引擎 md5 `e0c6f250…` 未变、`/health ok`、restarts=0）。
保留：`W904 §2` 的 dp4a 实测上限（19.07 TMAC/s）、`§7.2` 的资源占用表、`§7.4` 的方法教训，
以及可复用的两个工件（`albus/w904/patch_q4k_hoist.py`、`build_r51.sh`）。

**后继条目 R58（不是本条的延伸，另立）**：先把真实 `vec_dot` 拆成「解包 / 载入 / 缩放」三段并**逐段计数**，
只有某一段占比 >50% 且能单独消除时才动代码；在此之前不再对 MMQ 做结构改动。

## 9 复现

```bash
# 补丁 + 构建（容器内）
cp -a <llama.cpp>/ggml/src/ggml-cuda /work/r51-gc
python3 patch_q4k_hoist.py /work/r51-gc
# mounts: /src /build /llama /ov=/work/r51-gc /work
bash build_r51.sh
```
