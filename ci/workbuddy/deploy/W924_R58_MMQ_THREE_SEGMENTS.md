# W924 · R58：MMQ Q4_K 的 `vec_dot` 三段计数 —— 判据不满足，但产出两条硬结论

> **【AUDIT24 P1 · 2026-11-04】分母必须标口径**：「dp4a 占 53.3%」是**整个 mmq-instance 模块**求和
> （多 J、fallback 实例全算），而生产只 dispatch 一个 kernel —— `W943` 换成真 kernel 后是 **30.0%**，
> `R84` 的端到端上限随之从 −3.65% 改判 **−2.05%**。本件「无单段过半」的三段计数经 `W939` 复核仍成立；
> 但凡引用 53.3% 的地方，必须同时写"模块口径"。

日期：2026-11-04 00:1x – 00:4x
状态：**DONE_NEG**（无 >50% 的段，不动码）；顺带把 R60 的关闭依据从"微基准外推"升级为"真实 ISA 计数"

---

## 1 源码侧：三段本来就写在代码里

`vecdotq.cuh:533` 的 `vec_dot_q4_K_q8_1_impl_mmq`：

```cpp
for (int i = 0; i < QR4_K*VDR_Q4_K_Q8_1_MMQ/QI8_1; ++i) {   // 4 轮
    int sumi_d = 0;
    for (int j = 0; j < QI8_1; ++j) {                        // 4 次
        sumi_d = ggml_cuda_dp4a((v[j] >> (4*i)) & 0x0F0F0F0F, u[i*QI8_1 + j], sumi_d);
        //                      ↑解包 2 条            ↑激活
    }
    const float2 ds8f = __half22float2(ds8[i]);
    sumf_d += ds8f.x * (sc[i] * sumi_d);      // 缩放
    sumf_m += ds8f.y *   m[i];
}
```

每轮 `i`：**4 条 dp4a + 8 条解包（移位/掩码）+ 5–6 条浮点缩放**。
按源码手算解包占比 ≈ 44%（8/18）、浮点 33%、dp4a 22% —— 但这只是"一个 tile 内的比例"，
真实内核还有地址计算、LDS 载入、循环控制，必须看 ISA。

## 2 ISA 侧：真实计数（`mmq-instance-q4_k.cu.o`，54 个内核）

先 `llvm-objcopy --dump-section=.hip_fatbin` 再 carve（`objdump -d` 直接看只会出 x86 host 代码 —— 这是坑）。

| 指令 | 数量 | 占 dp4a |
|---|---|---|
| **`v_dot4_i32_i8`**（本体） | **5,184** | 100% |
| 解包：`v_and_b32` 871 + `v_lshrrev_b32` 368 + `v_lshlrev_b32` 198 | **1,437** | **27.7%** |
| LDS 载入：`ds_read_b32` | 1,204 | 23.2% |
| 缩放：`v_mul_f32` 596 + `v_fma_f32` 308 + `v_mac_f32` 96 + `v_cvt_f32_f16` 64 | **1,064** | **20.5%** |
| **地址计算**：`v_mul_lo_u32` | **824** | 15.9% |
| 标量载入：`s_load_dword` 255 + `_x2` 76 + `_x4` 7 | 338 | 6.5% |

**`v_mul_lo_u32` 的归属**（这一条必须查，不然分类错）：反汇编上下文是

```
v_mul_lo_u32 v18, s29, v5      // s29 = 步长(SGPR)，v5 = 索引(VGPR)
v_lshl_add_u32 v20, v7, 2, 0
```

⇒ **地址计算**，不是缩放。而且它用的是 **VALU 做"标量×向量"** —— 这正好是 `R63`（`readfirstlane` SGPR hoisting）要消除的那类。

## 3 判定：**判据不满足，不动码**

R58 的判据是「某段 >50% 且可单独消除才动码」。最大的一段是解包 **27.7%**，**没有一段过 50%** ⇒ **DONE_NEG**。

这不是坏消息：它把"要不要重写 Q4_K 解包"这条**彻底关掉**了 —— 与 `R51` 的实测（改 Q4_K 解包后 prefill 慢 6–10%）互相印证。

## 4 副产品一（重要）：R60 的关闭依据从"外推"升级为"实测配比"

用真实 ISA 算，不再用微基准：

```
VALU 指令 = dp4a 5184 + 解包 1437 + 缩放 1064 + 地址 824 = 8,509
MAC       = 5184 x 4 = 20,736
MAC/指令  = 20,736 / 8,509 = 2.44
```

```
峰值指令率 6.624 T instr/s x 2.44 MAC/instr = 16.2 TMAC/s 的 VALU 上限
生产 MMQ 相位 13.2 TMAC/s / 16.2 = 81%
```

**⇒ VALU 利用率 ≈81%，远高于 R61 的 40% 门** ⇒ **R60（stream-k）确认不做**。

对比 `W916` 当时的推算：它假设"每 MAC 再加 2 条 VALU 则超 100% 不可能"，只能推出 50–65%；
现在用真实指令配比算出 **MAC/指令 = 2.44（即 0.41 instr/MAC）**，比 `W904` 微基准的 0.75 instr/MAC 好 45%，
所以 VALU 上限比我先前估的更低、占用率更高。

**口径**：这仍是静态计数推算（不含 LDS 等待、不含量化拆包在 LDS 上的开销），不是 PMC。
但它比"按微基准外推"硬，因为分子分母都来自同一个真实内核。

## 5 副产品二：`R63` 有了精确靶子

地址计算 `v_mul_lo_u32` **824 条 = 15.9%**，形态是 `s29 × v5`（标量步长 × 向量索引）。
如果那个索引在 warp 内是 uniform（MMQ 的 tile 地址通常如此），用 `__builtin_amdgcn_readfirstlane`
把它提到 SGPR 再用 `s_mul`，就能把这 15.9% 从 VALU 移到标量单元。

**这就是 `R63` 要做的第一件事**，而且现在有明确的量化上限：**≤15.9% 的 VALU 指令**，
对应指令率上限从 2.44 提到 2.44/(1-0.159) = **2.90 MAC/instr（+19%）**。
但注意：VALU 已 81% 占用，理论上限也就 +19% × (1/0.81) 的有效空间 —— **实际能不能拿到要看 LDS 是否成为新瓶颈**。

⇒ `R63` 保留，判据改为：先用 `readfirstlane` 改地址计算，看 ISA 里 `v_mul_lo_u32` 是否真的消失（路径断言），再看 prefill。

## 6 复现命令

```bash
OBJ=~/strata166/gfx029-build/CMakeFiles/strata_mmq.dir/llama.cpp/ggml/src/ggml-cuda/template-instances/mmq-instance-q4_k.cu.o
docker run --rm -v $OBJ:/tmp/q4k.o -v /tmp/carve_elf.py:/tmp/ -w /tmp strata-gfx906:0.2.9-101 bash -lc '
  llvm-objcopy --dump-section=.hip_fatbin=fat.bin q4k.o
  python3 carve_elf.py fat.bin cos
  llvm-objdump -d cos/*.elf > dev.txt        # 54 个内核
  for p in v_dot4_i32_i8 v_and_b32 v_lshrrev_b32 v_lshlrev_b32 \
           ds_read_b32 v_mul_f32 v_fma_f32 v_mac_f32 v_cvt_f32_f16 v_mul_lo_u32; do
    printf "%-18s %6d\n" $p $(grep -c $p dev.txt); done'
```

**坑**：直接 `llvm-objdump -d xxx.cu.o` 只出 x86 host 代码（33,045 行，`endpgm` 0 个），
必须先 `--dump-section=.hip_fatbin` 再 carve。
