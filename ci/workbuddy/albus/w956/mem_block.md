## W956 · R90-S3：0.8.0 全量链接成功（17:5x–18:2x）

- 分支 `exp/R90-080`（worktree `work/r90-080`），部署分支与生产未动。
- **0.4.1 → 0.8.0 的 API 差异共三类**（全是 `#3217` 的 `ggml_prec` 透传 + 一个 pool 签名）：
  ① `ggml_cuda_mmq_get_config(...)` 多第 5 参 `ggml_prec`；② `mul_mat_q_case<T, prec>` 模板多一个参数；
  ③ `ggml_backend_cuda_context::new_pool_for_device(ctx, dev, stream)` 从两参改成三参静态成员。
  上游约定：K-quant 一律 `GGML_PREC_Q8`（与我们 Q8_1 激活对应）。
- **改动规模：6 文件 +35/−35 行**（moe_mmq.cu 25、mmq_kq_lib.cu 4、moe_mmq_tab.cuh 3、ggml_cuda_host.cu 1、nvfp4_w4a{8,4}.cu 2）。
- 结果：`ninja strata` **0 error**，产出 **39,599,200 B**；`./strata --version` = 0.1.56、`serve --help` 286 行 RC=0。
- 另：`cmake/strata_ggml_tq_overlay.cmake` 的锚点改成按枚举名匹配 + 套不上就 FATAL（commit `55a1acd4`，tag **r30**）；
  overlay 的 **trellis 段本身**也要适配 0.8.0 的 `ggml_cuda_mmq_util_funcs` ctor ⇒ 本轮 A/B 显式 `-DSTRATA_MMQ_TQ_OVERLAY=OFF`（trellis 不在模型里）。
- 余下 S4：逐位（贪心 64 token argmax 与 0.4.1 比）+ 六长度档 A/B，需 1 次停服（≈4m20s 重载 + 40–60 min 测量）。
- 台账 `audit_closure.py` 36/36；账本 176 条 / 已结 101（57.4%）；R90 仍 INFLIGHT。
