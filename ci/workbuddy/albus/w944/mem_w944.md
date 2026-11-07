
## W944 · 重新评估：漏了布局层（weight repack），"MMQ 只剩 attention" 撤回（15:0x）
- **认错**：上轮只查指令层（tile/内层循环/dot 指令），且只看了 llama.cpp 上游 + milpster/iacop 的 MMQ 内层；**布局层从未进清单**。
- **关键外证**：`mxxm-t/mx-llama.cpp`（mixa3607 新家，基线 upstream b11553）在 gfx906 默认开 **weight repack**（quants 与 scales 分平面、行去别名）：**Q5_1 +84%（单卡）/+74%（双卡 tensor）prefill**、Q6_K +69%、Q5_K +55%、**Q4_K 仅 +2~5%**；明确写「Qwen3.8-Flash-Next MoE 带 43 个 Q5_1 tensor ⇒ **+11% prefill（四卡）**」。
- **本机格式分布（新实测，native_experts.txt）**：gu = Q4_K 47 层 + Q5_K 1 层；down = **Q5_1 43 层（88.6% 专家字节）** + Q8_0 5 层 ⇒ 我们最重的格式正好是外证收益最高那档。
- **本机 canonical 基线（A 级）**：Q5_1 down [2560,640]、16 专家×320 token=5120 rows ⇒ **1.53 ms = 5.47 TMAC/s（峰 25%）**；Q8_0 down 4.70（22%）；Q4_K gate/up 6.5-7.4（30-35%）⇒ Q5_1 供给率最低，与 +84% 同向。
- **另两项外证**：q8_1 激活复用 +2.2~2.6%（bit-exact）→ 新立 **R87**；BF16→F32 compute +18~19% —— **我们已满足**（gemm.cu 全 CUBLAS_COMPUTE_32F/HIPBLAS_COMPUTE_32F）。
- **重评结论**：R61（VALUBusy 67.1%）/R60/R63/R84 结论**维持**（milpster 四家族全回归、LDS-wait 2.2%、occupancy 关闭，与本机 PMC 互证）；但"MMQ 五门全关 ⇒ 只剩 attention"**撤回** —— 正确说法是**指令层五门全关、布局层从未开门**。
- **新条目**：**R86（P0，Q5_1 repack）**、**R87（P1，q8_1 cache）**；队列改为 R86 → R85 → R64 → R87 → R72 → …
- **方法教训**：看 kernel 要同时看「怎么算」和「数据怎么摆」；取样要**按格式**（搜 "Q5_1 gfx906 prefill"），不要只按关键词（"MMQ gfx906"）。
- 账本：171 条 / 已结 104 = 60.8%；主线 143 / 104 = 72.7%。
