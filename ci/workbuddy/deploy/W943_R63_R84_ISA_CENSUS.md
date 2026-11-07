# W943 · R63 结题（ISA 计数：无可消项）+ **R84 改判**（分母换成真 kernel 后落到门下）

> **【AUDIT24 P1 · 2026-11-04】类别百分比加不拢**：§31 写「地址 ≈19.7%」，但同段列出的地址类指令
> 326+132+61+60+33+16 = **628 / 3,411 = 18.4%**；19.7% 是上一轮**模块口径**的遗留数。
> `W945 §7` 与 `R86` 的路径断言引用了 19.7%，应改用 **18.4%**。
> 另：本件据 ISA 静态计数把 R63/R84 判 DONE_NEG，按纪律⑱ 已由 `W947` 重开（R63=OPEN、R84=INFLIGHT）。

- 日期：2026-11-04 14:2x–14:3x
- 对象：`mul_mat_q<(ggml_type)12, 64, false>`（Q4_K，J=64）—— 就是 `W942` PMC 里占 98.59% 的那个 kernel
- 来源：`build-r28/kq_bench`（自建产物）的 fatbin，carve 出 21 个 gfx906 object，`co_011` 命中，窗口 `0x47400 + 0x5a7c`
- 铁律 ⑯：先 `cp /out/kq_bench /tmp/kq_copy` 再 `objcopy`，**没有碰生产件**

---

## 1 指令构成（3,411 条）

| 指令 | 条数 | 占比 | 归类 |
|---|---:|---:|---|
| **`v_dot4_i32_i8`** | **1,024** | **30.0%** | **dot** |
| `v_add_u32_e32` | 326 | 9.6% | 地址 |
| `ds_read2_b32` | 304 | 8.9% | LDS（双通道） |
| `v_fma_mix_f32` | 256 | 7.5% | 缩放 |
| `s_waitcnt` | 205 | 6.0% | 同步 |
| `v_mul_lo_u32` | 132 | 3.9% | 地址（64 位） |
| `v_cvt_f32_i32` | 128 | 3.8% | 解包/缩放 |
| `v_mov_b32` | 106 | 3.1% | 搬运 |
| `v_and_b32` | 80 | 2.3% | 解包 |
| `v_mul_f32` / `v_fma_f32` / `v_add_f32` | 64 / 64 / 64 | 5.6% | 缩放 |
| `v_addc_co_u32` + `v_add_co_u32` | 61 + 60 | 3.5% | 地址（64 位） |
| `global_load_dword` | 40 | 1.2% | 取数 |
| `v_ashrrev_i32` / `v_lshrrev_b32` | 37 / 36 | 2.1% | 解包 |
| `v_lshlrev_b64` / `v_lshl_add_u32` | 33 / 16 | 1.4% | 地址 |
| `ds_write_b32` / `ds_read_b32` / `ds_read_u16` | 23 / 16 / 7 | 1.3% | LDS |
| `buffer_load_dword` / `buffer_store_dword` | 10 / 10 | 0.6% | 取数 |

按类汇总：**dot 30.0% · 地址 ≈19.7% · 缩放 ≈13.1% · LDS ≈10.6% · 解包 ≈8.4% · 同步 6.0% · 搬运 3.1% · 其余 ≈9%**。

## 2 R63 结题：readfirstlane / prefetch 都**没有可消项**（A 级）

| R63 的两个候选手法 | 本 kernel 的实际状态 | 结论 |
|---|---|---|
| `__builtin_amdgcn_readfirstlane` SGPR hoisting | `v_readlane` / `v_readfirstlane` / `v_writelane` 全部排在 top-25 之外（**≤15 条，≤0.4%**）；`s_load_dword` 只有 **2 条** ⇒ 地址与基址本来就在 SGPR/常量里 | **无可消项** |
| inline-asm `global_load_dword` Y-tile prefetch | `global_load_dword` 40 条 + `buffer_load_dword` 10 条，已是常量偏移形态；`ds_read2_b32` 304 条说明 LDS 已是双通道读 | **已经是目标形态** |

⇒ **R63 = DONE_NEG**（判据是"无可消项 ⇒ 关"，`W832` 原文就写了）。这也解释为什么 iacop 的两个内层手法在我们的 K-quant 路径上 `0` 命中不是遗漏，而是**没有对应的问题**。

## 3 R84 改判：分母从「模块总和」换成「真 kernel」，2.05% < 3.2% 门

| 口径 | dot4 占比 | ⇒ 指令减少（减半） | ⇒ kernel（×67.1% VALU） | ⇒ 端到端（×20.4%） |
|---|---:|---:|---:|---:|
| `W924` 模块求和（5,184 / 9,713） | 53.3% | −26.7% | −17.9% | **−3.65%**（初稿） |
| **本 kernel（1,024 / 3,411）** | **30.0%** | **−15.0%** | **−10.1%** | **−2.05%** |

**−2.05% 落在 2×CV 门（3.2%）以下**，乐观情形（int4 权重顺带省掉 `v_and`/`v_lshrrev` 一类解包指令 ≈ 再 −3.4% 总指令）也只到 **−2.4%**。

⇒ **R84 判 DONE_NEG（不做）**。R74（W4A4 精度门）随之挂起 —— 没有内核要接，精度门就不必先付。

**为什么必须改判**：`W924` 数的是整个 `mmq-instance-q4_k.cu` 模块（多个 J、fallback=true/false 的实例全算进去），而生产只 dispatch 其中一个。**用模块总和当分母，会把一个"不值得做"的优化算成"刚好过门"。** 这正是 `W925` 分母纪律要补的一条：

> **组件占比的分母，必须是实际 dispatch 的那个 kernel；模块/实例库的求和只能当"上界的上界"。**

## 4 剩下的真靶子（本 kernel 内，且 R51 已警告不要乱动）

| 段 | 占比 | 备注 |
|---|---:|---|
| 地址运算（`v_add_u32` + `v_mul_lo_u32` + 64 位进位链） | **19.7%** | 比"解包"更值得看，但 `R51` 的 hoist 先例是**实测变慢 6–10%** ⇒ 要动必须先做 tile 级微基准 |
| 缩放（`v_fma_mix_f32` 256 + 128 条 fp32） | **13.1%** | `v_fma_mix_f32` 是 fp16/fp32 混合，已是最优指令形态 |
| 解包（`v_and` / `v_cvt` / `v_ashr`） | **8.4%** | `R51` 已判：提出 j 循环实测慢 6–10% |
| 同步 `s_waitcnt` | 6.0% | 205 条；`R60` 的 stream-k 会改它，但 `W942` 已判 VALU-bound、不做 |

⇒ **MMQ 这条线到此为止**：`R60`（stream-k）死、`R63`（内层手法）死、`R84`（dot8）门下、`R51`/`R58` 已判。prefill 再往上只能走 **attention（R46/R64）** 与 **GDN/入口**，这正是 `R85` 的方向。

## 5 复现

```bash
docker run --rm -v ~/strata166/build-r28:/out -v /tmp:/tmp -w /out strata-gfx906:0.2.10-101 \
  bash -c 'cp /out/kq_bench /tmp/kq_copy && llvm-objcopy --dump-section=.hip_fatbin=/tmp/fat.bin /tmp/kq_copy \
           && python3 /tmp/carve_elf.py /tmp/fat.bin /tmp/co'
# co_011_off5943296.elf: mul_mat_q<(ggml_type)12, 64, false> @ 0x47400, size 0x5a7c
llvm-objdump -d --no-show-raw-insn --start-address=0x47400 --stop-address=0x4ce7c /tmp/co/co_011_off5943296.elf
```
