## W835c　Strata 自身可扩展到 gfx906 的部分 + 四项开关实测（2026-10-31 15:0x–15:35）

- **结构性事实**：`src/core/arch_defaults.cpp:25-93` 先 `if(gfx12){RDNA4 表 9 项}`，再
  `if(!gfx_arch_is_gfx1151) return t` —— **gfx906 在此直接 return 空表**。全库只有 4 个架构谓词
  （gfx12 16 / gfx11_wmma 9 / gfx1151 5 / gfx12_wmma 3），**没有 gfx906 谓词**；
  gfx906 的识别全靠业务代码里写字符串 `gfx_arch_is(arch,"gfx906")`（`qsa_decode_attn.cu` 15 处）。
- **缺口分三类**：
  - **A 纯实现缺口**（kernel 无架构门控、只是进不了表，全是纯 getenv）：
    `ATTN_LANECELL`(`qsa_decode_attn.cu:916/1161`)、`TSUM`(`fused_gr.cu:2259` + `iq_kernels.cu:6270`)、
    `ATTN_MERGE_V2`(`:929`)、`EXPDEC`(`iq_kernels.cu:2432`)；
    另有 `HC_UPMIX`（`prefill/kernels.cu:2295` gfx11 版 + `:2367` sm_80+ 版，**无 gfx906 版**，纯算子融合、prefill 路径）、
    `GDN_CHUNKED`（`:1675` 仅 `__gfx1100__..__gfx1151__`，用 wmma，**算法可 fp32 重写**）、
    `GRAPH_PRIO`（`core/verify.cpp:219` 逐字 `#if defined(STRATA_USE_HIP)||defined(STRATA_HIP_GFX906)||defined(STRATA_GPU_METAL) return false`，
    注释 every HIP caller is guarded off）、conversation ckpt/park 异步族（#3779 逐字 "CUDA only, on HIP gfx906 and Metal they are off"）。
  - **B 硬件不符**：`qsa_select` 的 gfx11/gfx12 scorer（`v_wmma_f32_16x16x16_bf16_w32`，gfx906 无 WMMA）、
    `GDN_TC`、`PF_FUSED_F16`。
  - **C 路径不适用**：`DEQUANT_WIDE` 看似纯赚（按 CUDA compute capability 6.1/8.6/8.0 判，HIP 上恒 OFF；
    sm_86 短提示 TTFT −12~−17%、sm_80 prompt +4~7%，均 bitwise），**但我们 `MMQ_KQ=1` 走 `prefill.cpp:1836
    if (mmq_plan().any)`，不解包成 bf16 ⇒ 那条 dequant 路径用不上**，判不适用。
- **实测（5 臂，每臂 8×128 tok + 3 档 read，base/base2 复测）—— 负结果**：
  decode 中位 base 51.65 / base2 51.70 / tL 51.60 / tLT 51.60 / tL4 51.70 ⇒ **四项全部零收益**；
  read 6666 tok：base **9707** / base2 **9708（复现 0.01%）** / tL **10156(+4.6%)** / tLT 10199(+5.1%) / tL4 10123(+4.3%)。
  **tL 单项已退化，再叠加另三项无进一步变化 ⇒ 退化由 `ATTN_LANECELL` 单项造成**；三个长度均退化且随长度放大。
  ⇒ **全部不采用**。对照 gfx12 表声明四项合计 +3.5% bitwise ⇒ **同批开关在 gfx906 上是 0/−4.5%**。
- **新纪律**：`bit-identical` 只保证答案不变，**不保证不变慢**；`arch_defaults` 每一行都是本卡实测，
  **不可从 gfx1151/gfx12 的表推导**。凡来自别的架构的开关，先**单项**测，禁叠加测（本次叠加掩盖了归因）。
- **顺带修数据**：`PARAM_REGISTER.tsv` 有 4 行 W823/W824 时期的叙事段落（各占 1 列，会让按 11 列解析出错），
  已原样移到 `deploy/params/PARAM_REGISTER_ORPHAN_LINES.md`；TSV 现 **219 行、全部 11 列、无坏行**，备份 `.bak-w835`。
- 登记 **P221（PROPOSED）/ P222（REJECTED）**。生产未改动（0.2.8p2 / n2 / 33 args / 14 env / 7463 槽）。
