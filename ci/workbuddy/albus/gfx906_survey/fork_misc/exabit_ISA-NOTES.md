# What the Vega 7nm ISA says about gfx906, and whether llama.cpp uses it

A review of `reference/amd-vega-7nm-isa-gfx906.txt` and `reference/llvm-amdgpu-backend-user-guide.txt` against the kernels llama.cpp's HIP backend runs on this box, with the measured utilisation from `reports/`. Line numbers refer to the text files; the `.toc.md` files map them to PDF pages.

## 1. The hardware as the ISA describes it

| Fact | Source | Consequence for llama.cpp |
|---|---|---|
| Wavefront = 64 work-items; SALU handles all control flow | ISA 1.1, 2 (lines 378–470) | warp size is 64, not 32: a "warp reduction" is over 64 lanes, and kernels that assume 32 lanes per warp waste half the SIMD |
| 64 KB LDS per CU, 32 banks × 512 × 4 B | ISA 2.2.1 (line 503) | MMQ tiles stage weights through LDS; the 64 KB limit and 32-way banking set the tile shapes that avoid conflicts |
| VGPRs V0–V255 and 16–102 SGPRs per wave; VGPRs allocated in groups of 4 | ISA 3.1 state table (line 589), 3.6 (lines 894–935) | the 256-register file is shared by the waves resident on a SIMD, so a kernel's VGPR count sets how many waves can hide memory latency |
| New in Vega 7nm: `V_DOT4_I32_I8`, `V_DOT4_U32_U8`, `V_DOT8_I32_I4`, `V_DOT8_U32_U4`, `V_DOT2_I32_I16`, `V_DOT2_F32_F16`, `V_FMAC_F32`, `V_XNOR_B32` | ISA preface p.9 (lines 293–330), VOP3P table (lines 7943–7962) | `V_DOT4_I32_I8` is the dp4a llama.cpp's quantised matmuls are built on: 4 int8 MACs per lane per instruction |
| Packed 16-bit math: `V_PK_FMA_F16`, `V_PK_MUL_F16`, `V_PK_ADD_F16`, integer `V_PK_MAD_I16` …; `V_MAD_MIX_F32` for mixed 16/32-bit | ISA 6.7 (line 2326), VOP3P (line 7814) | fp16 runs at 2× the fp32 rate when it is packed two-per-Dword; unpacked fp16 runs at the fp32 rate |
| No matrix (MFMA) instructions | the ISA lists no `V_MFMA_*`; the LLVM guide files gfx908 / MI100 under "CDNA 1" (lines 531–533, 12455), the generation that introduced MFMA | no tensor-core flash-attention or MMQ path; the "mma" kernels in ggml-cuda never run here |
| DPP and SDWA operand modifiers, with a short exclusion list | ISA 12.19 (line 11494) | cross-lane shuffles can be DPP row operations instead of `ds_bpermute` through LDS; none of the excluded opcodes are the fp32 adds a reduction uses |
| Target features `sramecc`, `xnack`; code-object IDs `gfx906:sramecc-:xnack-` etc. | LLVM guide lines 505, 2030 | code objects must match the device's ECC/XNACK mode or the loader rejects them (a failure, never a slow path) |
| The `gfx9-generic` target **excludes** `v_dot4_i32_i8`, `v_dot8_i32_i4`, `v_fmac_f32` on gfx906 | LLVM guide lines 798–812 | a build for `gfx9-generic` has no dp4a; llama.cpp must be built for `gfx906` explicitly (`GPU_TARGETS=gfx906`) |

Peak rates that follow, per die at 1730 MHz with 64 CUs (4 SIMD × 16 lanes each, one wave64 VALU op per 4 cycles per SIMD, so 7.1 T lane-instructions/s): fp32 FMA 14.2 TFLOP/s (13.8 measured); packed fp16 28.3 TFLOP/s; int8 via `V_DOT4` 56.7 TOPS; int4 via `V_DOT8` 113 TOPS. HBM2: 1024 GB/s nominal; 840 GB/s in the first report's plain read, 880–892 read / 713–718 copy in the run-through's HIP probe at every power cap.

## 2. What the kernels achieve here

| Phase | Kernel | Stock b10288 | Production build | Of peak (production) | Bound by |
|---|---|---|---|---|---|
| Prefill, Q8_0, 2048-token micro-batch | MMQ (dp4a tiles through LDS) | 848 tok/s = 11.6 TOPS per die | 1130 tok/s = 15.4 TOPS per die | 27% of int8 | the 200 W cap; the fork's gfx906 tile table is worth 33% at the same power |
| Prefill attention, head 256 | flash-attention (fp16, no MMA) | 8.3 TFLOP/s per die | same | 60% of fp32 FMA, 30% of packed fp16 | kernel |
| Decode, one stream, one die | MMVQ, 1 column | 588 GB/s | +1% | 66% of the 890 GB/s measured read | bandwidth, as it should be |
| Decode, one stream, four dies | MMVQ + two RCCL allreduces per block | 21.9 ms/token | 21.5 ms: 11.2 MMVQ (604 GB/s) + 3.4 RCCL (128 × 27 µs) + 5.8 small kernels (1,300) + 1.1 idle (M1 trace, 2026-09-08) | 68% of HBM in the matvec; the die 95% busy | kernel count and the allreduce kernel, not launch gaps or the environment (19 variables within 0.8%) |
| Decode, 8 columns, one die | MMVQ | 52.7 tok/s, 152 ms/step | 69.1 tok/s (+31%; 72.2 for the kernel on upstream) | ~3 TOPS | load instructions per dot product (see s.3) |
| Decode, 8 / 12 / 16 columns, four dies | MMVQ (stock: MMQ 16-tile from 9 columns) | 160 / 122 / 153 | 174 / 199 / 204 (+9 / +62 / +34%) | — | same; the plain 16-column patch needs 113 VGPRs and loses on a single die, which the hybrid table avoids |
| Decode attention at depth | flash-attention vec (f16 KV) | 369 GB/s per die of cache read | same | 41% of HBM | kernel |

The prefill figure proves the build is using `V_DOT4_I32_I8`: without it, ggml's dp4a fallback spends about 8 lane-instructions per 4 MACs, which caps a die at 7 TOPS. Q8_0 prefill being 13–16% faster than Q4_K_M and 28% faster than Q6_K on stock (42% and 37% on the fork) is the same instruction at work: Q8_0 blocks feed dp4a directly, the K-quants spend VALU instructions unpacking scales. Q4_0 and Q4_1 are the exceptions, +33% prefill and +11–13% decode, because their unpacking is a shift and a mask — and they cost 0.09 and 0.056 nats of KL against 0.036 for Q4_K_M, so the cheap unpack is bought with quality.

## 3. What the kernel work found (run-through s.9–11)

**The eight-column MMVQ step, diagnosed.** Static counts and hardware counters on one die: batch 1 → 8 raises VALU instructions per wave 157 → 637 (4.1×) and memory-read instructions 29 → 96 (3.3×) while waves per dispatch fall 14,100 → 11,900 and cycles per dispatch rise 2.25×; VALU busy is 20% and 30%, LDS wait negligible. So the kernel is not issue-bound: 70% of the time the SIMDs wait on loads, 96 per wave behind a 15-deep wait chain at the four waves per SIMD that 64 VGPRs allow.

**What moved it, and what did not.** The occupancy reading was wrong as a lever: rows-per-block 1 at any warp count halves registers, doubles waves in flight, and loses 20–36%, because each loaded activation block then feeds half as many rows. What won was fewer instructions per dot product — the Q8_0 fast path that loads each weight block's quants and scale once per row and each activation block's once per column and applies the two scales as one product per pair (+62% at 12 columns on the split) — and more rows per loaded block (rows 4, +36% at 8 columns on one die). Loading a whole 32-weight block per thread, a quarter of the load instructions, lost 16–32% at batch 8 because the dependent dot-product chain became four times longer (it wins only at batch 1, +5%). Staging one LDS copy of the activations per block lost 16–52%: the barrier. Aligned dword loads lost 9–17% with or without a branch. Rows 8 lost to register pressure. The rule: fewer instructions between load and accumulate wins; anything that adds a barrier or lengthens a dependent chain loses; registers beyond about 64 per thread lose. In ISA terms, GCN issues one VALU instruction per wave every four cycles per SIMD and hides load latency only with other waves' instructions or with independent work in the same wave; the winning kernel keeps four to eight independent dot-product chains per thread (rows × columns) inside a 64-VGPR budget, which is the point where the wait chain and the register file balance on this chip.

**The MMQ tile table.** Upstream's integer matrix kernel picks tile shapes from a generic table on gfx906; the ML-gfx906 fork's gfx906 table gives +33% prefill at Q8_0 and +26% at Q6_K with no change to the arithmetic. The 64 KB LDS with 32 banks and the wave64 layout set the tile shapes that avoid bank conflicts and keep four waves resident; a per-target table is the right upstream fix.

**Closed questions.** rocBLAS fp16 GEMM for prefill (`GGML_CUDA_FORCE_CUBLAS`) ties MMQ within the run-to-run band on a single die and was retired, as the energy argument in the previous version of this file predicted: `V_DOT4_I32_I8` is the most energy-efficient MAC on the chip and prefill sits at the power cap. `V_DOT8_I32_I4` stays unusable: it multiplies 4-bit by 4-bit and llama.cpp quantises activations to 8 bits. The `GGML_CUDA_FA_ALL_QUANTS` build runs the 4-bit value cache at head size 256 (q8_0 K / q4_0 V: −18% decode at 32K depth against f16, perplexity 5.619 vs 5.615) and is the first configuration that holds eight 256K contexts.

## 3b. What is left on the table

**Cross-die synchronisation and kernel count** — the single-stream levers, now measured (M1 trace, `reports/2026-09-08-m1-kernel-trace.md`): of the 21.5 ms token on four dies, 3.4 ms is 128 RCCL kernels at 27 µs, 5.8 ms is 1,300 small kernels at the ~4 µs dispatch floor, 3.6 ms is the matrix-vector kernels running at 68% of HBM, 1.1 ms is idle; nineteen environment settings moved it by less than 0.8% because the die is 95% busy. The fabric's one-hop read latency is 507 ns and a link carries 33 GB/s, so the few KB each block's allreduce carries could cross the ring in single-digit microseconds; the per-layer cost is 94 µs. The next step is a kernel-trace of one decode token (rocprofv3) to split the 13 ms into RCCL kernels, ggml kernels and gaps; then, depending on the split, a latency-optimised 4-die allreduce for ≤ 64 KB messages writing directly into peer VRAM over XGMI (fine-grained stores plus a flag, not the shader-pull ring the XGMI report found slow at gigabyte sizes), and fusion of the linear-attention blocks' small kernels. If the per-layer term fell from 94 µs toward 30, one stream would run at ~56 tok/s before MTP (+23%).

**Flash attention at head size 256** is at 30% of the packed-fp16 peak in prefill and 41% of HBM in decode. The ISA provides `V_PK_FMA_F16` for the QK and PV products and `V_DOT2_F32_F16` for fp32-accumulated dot products of fp16 pairs; the fork's tile-table lesson (a per-target table, no arithmetic change, +33%) applies to the FA tile kernel's tile shapes too. At 256K attention is 72% of prefill time and a third to 60% of a decode step, so this is the long-context lever.

**The Q8_1 activation scale inside the fast path.** Q8_1 carries a scale and a block sum; against Q8_0 weights only the scale is used, so quantising activations to Q8_0 for Q8_0 weights saves a 4-byte load and a multiply per block per column — a few percent on a kernel that is bound by instructions per dot product. The Q4_0/Q4_1/K-quant vec_dot paths have the same shape and no fast path yet; the K-quant unpacking (4- and 6-bit scales) is the place where `V_PK_*` integer ops and SDWA byte selects could replace shift-and-mask sequences.

**24- and 32-column decode** on the production build is unmeasured; those batches run the MMQ tile kernel whose table the fork changed. If the fork's table lifts them as it lifts prefill, `-np 32` becomes a 230+ tok/s setting.

**Reductions through LDS instead of DPP.** `__shfl_xor` compiles to `ds_bpermute_b32` on GCN, a trip through the LDS crossbar; DPP row shifts and `v_readlane` do the same in-register. Every kernel's final per-row reduction pays it. Small, and in every kernel.

**Verified once, fine.** The build target is gfx906 (the prefill rate proves dp4a is in use). HBM ECC does not cost bandwidth worth chasing: 880–892 GB/s of a 1024 nominal is the usual non-ECC HBM2 result.

## 4. The other reference documents

`amd-instinct-system-tuning-guide-57286` is for EPYC 7002 boards with MI50s on PCIe. On this Xeon W Mac Pro the transferable items are IOMMU passthrough (`iommu=pt`), disabling deep C-states (`cpupower idle-set -d 2`) so kernel launches do not wake a sleeping core, and confirmation that large-BAR/above-4G decoding is in effect, which the flat hive address space in the XGMI report shows. The xGMI-width, NPS and Preferred-IO settings are EPYC-only.

`amd-infinity-fabric-link-user-guide-56978` is the MI100 bridge installation guide. Its only bearing here is that four-card ring assemblies are the documented arrangement for Infinity Fabric Link; the Mac Pro's two-module bridge builds the same ring on Vega 20, as the XGMI report measures.
