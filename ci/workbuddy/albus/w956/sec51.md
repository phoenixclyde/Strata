
## 5.1 第二道坎：overlay 的 trellis 代码与 NVFP4 TU

修好锚点后 overlay 真的生效了，接着冒出两个新错误：

1. `src/prefill/mmq_nvfp4_w4a8.cu`（Blackwell sm_120 的 W4A8 路径，与我们 gfx906 无关）也调 `mul_mat_q_case`，
   补 `GGML_PREC_Q8` 即过；
2. 但它的报错把**overlay 生成的 trellis 代码**暴露出来：`ggml-tq-overlay/mmq.cuh:699/880/964` 的
   `ggml_cuda_mmq_util_funcs` 构造与 `get_util_funcs` 在 0.8.0 上也多了 `prec` 参数 ⇒ **overlay 的 trellis 段同样要再做一遍适配**。

**决定（并写清理由）**：R90 的 A/B 用 **`-DSTRATA_MMQ_TQ_OVERLAY=OFF` 显式关闭**，因为

- trellis（`TQ2_T/TQK6/TQK7/TQP5-7`）**不在我们的模型里**（专家是 Q4_K/Q5_1/Q8_0），
- 关掉是**显式**的（`W955` 加的 fail-hard 正好保证"要么生效、要么报错"，不会静默），
- 适配 trellis ctor 是独立的一小块，等真要跑 trellis 模型再做，不拖累主线。

⇒ **这条也回答了"0.8.0 迁移要改多少"**：我们的 MoE 路径 28 处；trellis overlay 另有一小块（未做，不影响本模型）。
