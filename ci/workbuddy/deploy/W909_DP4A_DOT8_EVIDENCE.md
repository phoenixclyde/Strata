# W909 · v_dot4_i32_i8 / v_dot8_i32_i4 我们到底有没有（源码 + 二进制 + 硬件三层实证）

> **【AUDIT24 P0 · 2026-11-04】§5 与 §6.4 的「专家格式」判断作废（算术已复核）**：日志里的
> `MMQ tile: type 20/21/23/8` 是引擎**按类型×J×cap 打的一次性能力表**（实测 4 类型 × 5 cap = **20 行**），
> 不是"本模型专家的类型"。权威来源是 pack 描述符 `native_experts.txt`，且它的**逐专家字节能精确对上算术**：
> `3,072,000 B = Q4_K gate/up 1,843,200 + Q5_1 down 1,228,800`（Q8_0 down 的层则是 3,584,000）。
> ⇒ 专家是 **Q4_K×47 + Q5_K×1（gate/up）／ Q5_1×43 + Q8_0×5（down）**，**没有 IQ 码本类型**。
> ⇒ §6.4「dot8 对 IQ 码本类型连 W4A4 都用不上」**不适用于我们的专家**（线性 4-bit，可用）；
> dot8 的否决结论已由 `W927`（W4A4 下指令减半）推翻，现由 `R84/R91` 在办。
> §1–§4 的指令/二进制/硬件三层证据（sdot8 语义、130,808 条 `v_dot4`、0 条 `v_dot8`）**不受影响**。

> 2026-11-03 03:0x–03:2x。零停服（只在生产容器里跑过 4 个 <1 s 的探针内核，未动进程、未改参数、未重启）。
> 全部数字都标了来源层级：**[ISA]** 官方文档/汇编输出 · **[SRC]** 我们自己的源码 · **[BIN]** 生产引擎反汇编 · **[HW]** 在这张 MI50 上实跑 · **[MB]** 我自己写的微基准。

---

## 0 先给答案

| 问题 | 答案 |
|---|---|
| `v_dot4_i32_i8`（= `dp4a` = `sdot4`）我们有吗？ | **有，而且一直在跑**。源码 152 个调用点；生产引擎二进制里 **130,808 条**静态实例，覆盖至少 2 个 483/712 内核的大 TU **[BIN]** |
| `v_dot8_i32_i4`（= `sdot8`）我们有吗？ | **硬件有、编译器有、代码里没有**。二进制 **0 条**、源码 **0 处** **[BIN][SRC]** |
| "tiled dp4a" 是差距吗？ | **不是**。我们已有 pointer-table tiled MMQ，9 个类型，正是本模型用的 IQ4_NL/IQ3_S/IQ4_XS **[SRC][LOG]** |
| "tiled dp4a + v_dot8" 是 gfx906 最优路径吗？ | **前半对且已在做，后半不成立**。`v_dot8` 是 **i4×i4**，W4A8 下用它指令数不减、还多一次拆包；IQ 码本非线性，连 W4A4 都用不上 |
| 那真差距在哪 | 同一张卡、同一条 dot4 指令：实测峰 **21.52 TMAC/s**，我们生产折算 **4.55 TMAC/s = 21%**；hipfire 同卡 prefill MMQ 到 **48.5% VALU** ⇒ 差距在**调度/供给**，不在指令集合 |

一句话：**指令早就有了，缺的是把它喂饱。** 所以 R61（PMC 判 VALU）→ R60（stream-k）→ R58（三段计数）的顺序不变。

---

## 1 先消歧：三个名字 = 两条指令

`dp4a`、`sdot4`、`v_dot4_i32_i8` 是同一条指令在三个层面的叫法（CUDA 内建 / LLVM 内建 / 汇编写法）。`v_dot8_i32_i4` 是**另一条**指令（LLVM 叫 `sdot8`）。

官方签名（LLVM `AMDGPUAsmGFX906`，VOP3P 段）**[ISA]**：

```
v_dot2_f32_f16 vdst, src0::f16x2, src1::f16x2, src2::f32  neg_lo neg_hi clamp
v_dot2_i32_i16 vdst, src0::i16x2, src1::i16x2, src2::i32  clamp
v_dot4_i32_i8  vdst, src0::i8x4,  src1::i8x4,  src2::i32  clamp
v_dot8_i32_i4  vdst, src0::i4x8,  src1::i4x8,  src2::i32  clamp
v_dot4_u32_u8  vdst, src0::u8x4,  src1::u8x4,  src2::u32  clamp
v_dot8_u32_u4  vdst, src0::u4x8,  src1::u4x8,  src2::u32  clamp
```

我们用本容器的 clang 直接编出来对了一遍 **[ISA/HW]**（`albus/w909/dot_isa_probe.cpp`）：

```
k_sdot4  ->  v_dot4_i32_i8 v1, s0, v1, v2
k_udot4  ->  v_dot4_u32_u8 v1, s0, v1, v2
k_sdot8  ->  v_dot8_i32_i4 v1, s0, v1, v2
k_udot8  ->  v_dot8_u32_u4 v1, s0, v1, v2
k_fdot2  ->  v_dot2_f32_f16 v2, s2, v1, v2
```

> 顺手纠一处官方文档自相矛盾：LLVM `AMDGPUUsage` 的 **gfx9-generic** 行把 `v_dot4_i32_i8 / v_dot8_i32_i4 …` 列进"not available on gfx906"，而 **gfx906 汇编语法页**把这两条逐字列在 VOP3P 表里。**以汇编页 + 实测为准**：gfx906 有这两条。gfx9-generic 那一行是通用目标的能力收敛描述，不能读成 gfx906 的实际能力。

---

## 2 硬件层：在这张 MI50 上真的跑通了 **[HW]**

`albus/w909/dot_hw_run.cpp`，容器内 `clang++ -x hip -mcpu=gfx906 -O2` 编译后直接执行：

```
sdot4  = 80 (expect 80)      OK
sdot8  = 20 (expect 36)      <- 我算错了，见下
sdot8- = -8 (expect -8)      OK signed i4
fdot2  = 13.50 (expect 13.5) OK
```

第二个用例是**本次最有价值的一次"失败"**：我给 `a` 的 8 个 nibble 是 `{1,2,…,8}`，按"每个都是正数"算应为 36，实得 **20**。20 = 1+2+3+4+5+6+7**−8** —— 也就是说 nibble `8` 被当成 **−8**。第三个用例（8 个 nibble 全是 `0xF`，即全 −1）得 **−8**，再次确认。

⇒ **`v_dot8_i32_i4` 的操作数是 4-bit 有符号整数，不是"int4 × int8"。**（这条与 `W908 §1` 一致，这里补上了硬件实证。）

---

## 3 源码层：我们有几处 **[SRC]**

垫片在 `include/strata/platform/hip_compat/strata_hip.h:236`：

```c
// __dp4a(a, b, c): signed 8-bit dot product plus accumulator; gfx906 has v_dot4_i32_i8.
static __device__ __forceinline__ int strata_dp4a(int a, int b, int c) {
#if defined(__gfx906__) || defined(__gfx908__) || … 
    return __builtin_amdgcn_sdot4(a, b, c, false);
#else
    … 四个标量乘加 …
#endif
}
```

调用点统计（`pr/strata-fork` @ `gfx906/mi50 d963c791`）：

| 位置 | 数量 | 说明 |
|---|---|---|
| `src/kernels/cuda/iq_kernels.cu` 经 `ggml_cuda_dp4a` 宏 | **114 处**（+1 处宏定义） | i-quant 的 vec_dot 与 dequant，转写自 llama.cpp `vecdotq.cuh` |
| `src/dsv41/{ds4_iq,ds4_gguf}.cu` 直接 `__dp4a` | 16 + 16 | DeepSeek v4.1 路径 |
| `src/kernels/cuda/{s2_gemv_q8,s2_expert_grouped,dflash2}.cu` | 1 + 1 + 3 | |
| `src/dsv41/vendor/exl3{,_legacy}.cu` | 1 + 1 | |

两条**必须记住**的编译行为，都是本次实测出来的 **[MB]**：

1. **标量回退会被自动融合**。我把 `strata_dp4a` 的 unsigned 重载（手写 4 个 byte 乘加，**没有**调 `udot4`）单独编，`-O3` 下 clang 直接给出 `v_dot4_u32_u8`。⇒ 这条分支没有性能债，但也说明**"源码里没写内建"≠"没用到指令"**，判断必须以反汇编为准。
2. **手写 8-nibble 循环不会被融合成 `v_dot8`**。同一份探针里 `shim_nibble8`（循环取 8 个 nibble 做乘加）编出来**没有任何 dot 指令**。⇒ 将来真要试 dot8，必须显式 `__builtin_amdgcn_sdot8`，指望编译器识别是不成立的。

---

## 4 二进制层：生产引擎里到底有多少条 **[BIN]**

方法（踩了两个坑，记下来）：

1. `llvm-objcopy --dump-section=.hip_fatbin=/tmp/fat.bin /data/bin/strata-0.1.55t` → 26,955,960 B，`clang-offload-bundler -list` 显示 **68 个 bundle**（每个 TU 一个）。
2. 新版 bundler 的 magic 是 ASCII `__CLANG_OFFLOAD_BUNDLE__`，不是 `0x0B17C0DE` ⇒ 自写脚本按 `\x7fELF` + `e_machine==224` 扫切（`albus/w909/carve_elf.py`）。
3. **坑**：切分长度必须取 `max(sh_offset+sh_size, e_shoff+e_shnum*e_shentsize)`。只取前者会切掉段头表，`llvm-objdump` 报 "section header table goes past the end of the file"，而我把 stderr 用 `2>/dev/null` 丢了 ⇒ 第一轮得出"0 条 dot"的**假结论**。修正后同一批文件：

```
carved 68 amdgcn code objects
v_dot4_i32_i8   130808      <- 真实值
v_dot8_i32_i4        0
v_fmac_f32       72017
v_fma_f32        21089
v_mul_lo_u32     32959
ds_read_b128     12766
总静态指令     3492465      内核 3145 个
```

**取证对象是"正在跑的那个"**：`cat /proc/15/exe > engine_run.bin`（md5 `e0c6f250…`，40,771,760 B）。
同时发现一件必须登记的事：**磁盘上的 `/data/bin/strata-0.1.55t` 不是运行中的那个** ——
磁盘件 md5 `a97f4479…`（40,746,776 B，mtime `Nov 2 19:01`），`readlink /proc/15/exe` 显示
`…strata-0.1.55t (deleted)`。两者的 **`.hip_fatbin` 逐字节相同**（md5 `b4f1e26a…`，26,955,960 B），
差的是主机侧约 25 KB ⇒ 本档案的所有指令计数对两者都成立；但**下一次重启会切到 `a97f4479…`**，
而它没有经过 A/B。建议二选一：确认它就是预期件，或把 `e0c6f250…` 复写回去。

按 TU 分布（前 4）：

| code object | 内核数 | v_dot4 |
|---|---|---|
| `co_042` | 483 | **44,730** |
| `co_016` | 712 | **37,464** |
| `co_041` | 31 | 5,888 |
| `co_057` | 54 | 5,184 |

**口径警告**：这是**静态**计数——每个内核按被编进去算一次，与实际运行时长无关。它的用途是"有没有、有多少处"，**不能**当作时间占比。时间口径仍要看 PMC（R61）。

两个副产品，直接喂给队列：

- `v_mul_lo_u32` **32,959** 条，是 `v_dot4` 的 25%。这正是 R58 要拆的"解包/移位/与"那一段的静态证据 —— 它确实不是零头，但 W904 已证明 hoist 反而更慢，所以只能先计数（R58 原样）。
- `v_pk_fma_f16` / `v_dot2_f32_f16` 在引擎里是 **0**。FP16 GEMM 全部走 rocBLAS（日志：`prefill gemm: rocBLAS tuning enabled (84 rows, 75 with a solution, gfx906, rocBLAS 5.7.0.962d0059)`）。⇒ 想把 dot2 拿进来是另一个话题，不在本条范围内。

---

## 5 "tiled dp4a" 我们是不是已经有 —— 有 **[SRC][LOG]**

`src/prefill/mmq_tab_instance.cu.in` 每类型一个 TU，实例化 `mul_mat_q_tab_case<GGML_TYPE_x>`；CMake `:2255` 的类型表：

```
q2_0 iq2_xxs iq2_xs iq2_s iq3_xxs iq3_s iq4_nl iq4_xs q8_0     (9 个)
```

生产日志（`/data/strata-huihui-ud-iq4_xs.log`）逐字：

```
strata: MMQ tile: type 21 -> J=64 (48000 B of shared, smpbo 65536, cap 0)
strata: MMQ tile: type 20 -> J=64 (48000 B of shared, smpbo 65536, cap 0)
strata: MMQ tile: type 23 -> J=40 (25056 B of shared, smpbo 65536, cap 0)
strata: MMQ tile: type  8 -> J=80 (50112 B of shared, smpbo 65536, cap 0)
```

type 20/21/23 = IQ4_NL / IQ3_S / IQ4_XS，正是本模型专家用的三种。`J` 是输出行方向的 tile，48,000 B 共享内存 ⇒ **LDS 分块 + 权重按 tile 复用**，与 llama.cpp 的 tiled MMQ 同构。

⇒ hipfire 报告里那句 "hipfire needed a tiled MMQ kernel adapted to gfx906 (no WMMA → use dp4a `__builtin_amdgcn_sdot4`)" 是他们**补课**的过程；我们这一段**已经在用**。所以"tiled dp4a"不是我们的差距项。

---

## 6 `v_dot8` 能不能用 —— 数学判决（不是偏好）

### 6.1 指令本身
`i4 × i4`，两个操作数各 8 个 4-bit 有符号数（§2 实测）。要用它，**权重和激活都必须是 4-bit**。

### 6.2 W4A8 下用不了：拆包不省指令
设激活 `a ∈ int8`，权重 `w ∈ int4`。想用 dot8 必须把 `a` 拆成两个 4-bit：

```
a = 16·h + l ,  h,l ∈ [−8,7]
⇒ Σ a·w = 16·Σ h·w + Σ l·w      (8 个元素需要 2 条 dot8)
```

而 dot4 走同样 8 个元素也是 **2 条**（每条 4 个 MAC）。**指令数完全相同**，dot8 版本还多两次拆包（`v_and` + `v_lshr` ×2）。
⇒ 用 dot8 换不来任何发射数，只增加 ALU。

### 6.3 拆分的可表示域也不闭合
`16h + l` 在 `h,l ∈ [−8,7]` 时覆盖 **连续的 [−136, 119]**；int8 的正端 120…127 **不可表示**。若把激活限到 ±119，那是**改量化方案**，不是改指令。

### 6.4 IQ 码本类型根本不允许
本模型的专家是 IQ4_NL / IQ3_S / IQ4_XS：权重存的是**码本索引**，`index → value` 是查表（非线性）。对索引做点积 ≠ 对值做点积 ⇒ **dot8 对这些类型连 W4A4 都用不上**。只有线性 4-bit（Q4_0/Q4_1/Q4_K 这类）才有资格谈 W4A4。

### 6.5 唯一合法路径是 W4A4，而那是精度决策
把激活也压到 4-bit：KL/top-1 代价未知，**R59 还没测出来**。在 R59 给出 `KL ≤ 0.005 且 top-1 ≥ 99%` 之前，W4A4 不能进方案。
（hipfire 自己也把 dot8 列在 Follow-up 第一项、标注未实现，原文：*"y would need to be int4-quantized too for the symmetric dp8"*。）

⇒ **结论：`v_dot8` 不是 gfx906 量化推理"最优路径"的一半。在 W4A8 下它是负收益；在 W4A4 下它是待定的精度问题；对 IQ 码本类型它根本不适用。**

---

## 7 量化：这张卡的真实上限（自己测，不引第三方）**[MB]**

`albus/w909/bench_dot.cpp`，60 CU × 256 线程 × 8 块/CU，ILP4，纯寄存器、无访存：

| 指令 | 实测 | 折算 | 占理论峰 |
|---|---|---|---|
| `sdot4` | 5380.26 Ginstr/s | **21.52 TMAC/s** | **81%**（理论 26.5） |
| `sdot8` | 6207.84 Ginstr/s | **49.66 TMAC/s** | **94%**（理论 53.0） |

- 指令率只差 **1.15×**，但 MAC 率差 **2.31×** —— 这正是 dot8 唯一的诱惑所在。
- 与第三方（skyne98 gfx906 wiki）同向：dot4 21.7–22.3、dot8（ILP4）85–86 TOPS = 42.5–43 TMAC/s。我们这张卡 dot8 还略高（49.7）。
- 与 `W904` 我自己先前测的 "dp4a 纯寄存器 19.07 TMAC/s" 有 13% 差距，原因是本次 ILP4 + 3 次重复取事件计时（W904 是 5 rep 的墙钟口径）。**以 21.52 为上限口径**，`W904` 的 19.07 记为保守值。

**差距量化**：生产折算 4.55 TMAC/s ÷ 21.52 = **21%**。若把 tiled MMQ 的 VALU 占比从 21% 提到 hipfire 的 48.5%，等效 10.4 TMAC/s；prefill 里 gemm 占 **34.6%**（gate/up 20.7% + down 14.0%，`W903`）⇒ 端到端**上限约 −16%**（粗算，仅供排序，不作承诺；以 R61 的 PMC 与 A/B 为准）。

---

## 8 对队列的影响

| 条目 | 影响 |
|---|---|
| **R61**（PMC 量 VALU） | **不变，且更该做**。现在有两把尺子：dot4 峰 21.52、dot8 峰 49.66；若我们 VALU ≤25% ⇒ 差距在供给，R60 必做；≥40% ⇒ 接近硬件墙 |
| **R60**（stream-k） | **不变**。它是"提高在飞字节/并发流"的手段，与指令集合无关 |
| **R58**（三段计数） | **获得静态支持**：`v_mul_lo_u32` 32,959 条 ≈ dot4 的 25%，解包段确实存在；但 W904 已证 hoist 更慢，所以仍按"先计数、不预设收益" |
| **新增 R62** | 本条即 R62：gfx906 dot 指令审计（源码/二进制/硬件三层），**DONE**，不产生内核改动 |
| **不新增** | 不立 "v_dot8 移植" 条目 —— §6 已判定在 W4A8 下负收益、在 IQ 码本下不可用；除非 R59 过 W4A4 精度门，否则不复活 |

---

## 9 复现（全部在 `strata166-407` 内，零停服）

```bash
# 1 指令是否存在、编出来是哪条
clang -x hip --cuda-device-only -mcpu=gfx906 -O3 -nogpulib -S dot_isa_probe.cpp -o -  | grep v_dot

# 2 硬件是否真的执行（这条最重要）
clang++ -x hip -mcpu=gfx906 -O2 --offload-arch=gfx906 dot_hw_run.cpp -o dot_hw_run && ./dot_hw_run

# 3 生产二进制里有多少条
llvm-objcopy --dump-section=.hip_fatbin=fat.bin /data/bin/strata-0.1.55t
python3 carve_elf.py fat.bin cos && for f in cos/*.elf; do llvm-objdump -d "$f"; done \
  | grep -oE 'v_dot[0-9a-z_]*' | sort | uniq -c      # 注意：不要 2>/dev/null，否则截断错误会被吞掉

# 4 同卡吞吐上限
clang++ -x hip -mcpu=gfx906 -O3 --offload-arch=gfx906 bench_dot.cpp -o bench_dot && ./bench_dot
```

产物：`albus/w909/{dot_isa_probe.cpp, shim_probe.cpp, dot_hw_run.cpp, bench_dot.cpp, carve_elf.py, split_bundle.py}`。
