## W835　gfx906 专项优化移植可行性（14:4x）

- **指令真值（166 上实跑 llvm-mc -mcpu=gfx906 裁定）**：`v_dot2_f32_f16` OK、`v_dot4_i32_i8` OK、
  `v_dot8_i32_i4` OK、`v_mov_b32_dpp` OK；`v_dot4c_i32_i8` NO、`v_mfma_f32_16x16x16_f16` NO。无 MFMA、无 bf16。
  ⇒ **LLVM 文档把 dot 列进"gfx906 不可用"是 gfx9-generic 的联合限制**（gfx900/902/904 没有），照字面读会判反。
- **生态里有一处流传很广的错**：KI 的 `csrc/rocm/dense_gemv_gfx906.cu:600` 注释逐字
  "gfx906 has no integer dot product, so the MACs run through the existing __ockl_fdot2 chain"
  ⇒ 它 AWQ W4A16 全走 fp16 dot2、完全没用 dp4a。**反例是我们自己**：`STRATA_DP4A` 走 v_dot4_i32_i8，
  `MMQ_KQ=1` 实测 **+68% prefill**（P198）。这条可直接回馈上游。
- **三方现状**：KI 在 `/home/albus/routeK/base/KIntegrated-mobydick@6ccbb03`，gfx906 专项在
  `csrc/gfx906_fa/`（vendored from cassettesgoboom/gfx906-fa-vllm，源于 skyne98）+ `csrc/rocm/*_gfx906.cu`。
  **llama.cpp 在 166 上只有 third_party/llama.cpp（ggml 3cf0325）与 mixa3607 的二进制镜像，无 fork 源码**
  ⇒ llama.cpp 这条线只能搬手法、不能搬代码（ggml 与 Strata 自研引擎不共享层）。
- **Strata 现状（49 个 .cu 全库计数）**：`__ockl_fdot2` **0 处**；`dpp` 仅 2 处（但 `qsa_decode_attn.cu:478`
  已用 `__builtin_amdgcn_mov_dpp` 替代 ds_bpermute，注释写明"score 循环被 LDS 管道卡住"）；`__shfl_xor` 193 处/31 文件；
  LDS 仅 **2 处** padding（`dflash2.cu:107 Sc[32*33]`、`qsa_select.cu so[][TS_KB+1]`）；
  **`fused_gr.cu:3101` 硬门 `prop.warpSize!=32` ⇒ HC_PERSIST 在 gfx906 上全关**（HC 占 16.6%）。
  已有 wave64 分支：`native_mmvq.cu:2343`、`router_top10.cu:191`、`qsa_decode_attn.cu:825`。
  ⇒ **不是零基础，是"部分完成 + 4 处空白"**。
- **可移植判断**：LDS +1 padding（skyne98 实测 1865→3974 GB/s）与 DPP 归约 **可直接搬**（纯布局/primitive）；
  fp16 dot2 **可搬但有精度代价**（GDN 现用 `__uint_as_float(w<<16)` + fmaf 做 bf16→fp32，改 fp16 会丢指数范围，须过 KL 门）；
  fused_gr 的 wave64 重写 **以周计**。
- **"别的架构优化→gfx906"**：开关这条路已证死（gfx1151 十项 → non-finite logits，P212）。
  正确分类：A 纯算法/布局=可扩展；B 需 wave primitive=可重写；C 需 MFMA/WMMA/bf16/FP8=不可扩展。
  owner 没卡所以 `arch_defaults.cpp` 留空是对的，我们该给他 gfx906 条目 + kernel 实现（可提 PR）。
- **预期**：按 44.98 ms/窗口相位表，可触及 33 ms(73%)，各项 30-50% ⇒ 合计 **-5%~-10%**（比开关类 ±1.5% 大一个档次）。
- **下一步第 0 步**：微基准（LDS ld=32 vs 33 / DPP vs bpermute / fdot2 vs f32-fma），不停服 ~30 min，
  先证明 gfx906 上的倍数与 skyne98 的一致，再改引擎。
- 文档 `deploy/W835_GFX906_PORT_FEASIBILITY.md`；登记 **P217（CONFIRMED）/ P218（PROPOSED）**，219 行。生产未动。
