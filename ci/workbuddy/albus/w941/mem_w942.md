
## W942/W943 · R61 结题：MMQ VALUBusy 67.1%（A 级），R60/R63 判死、R84 改判（14:0x-14:3x）
- **工具门彻底打通**：`rocprofv3` 当启动器 + **独立可执行自然退出** ⇒ csv 落盘。驱动 `~/strata166/w941/kq_bench.cpp` → `build-r28/kq_bench`（16 专家×1024 token=16,384 rows，Q4_K gate/up，链生产同一份 libstrata_mmq.a）。
- **实测**：`mul_mat_q<(ggml_type)12,64,false>` 占 98.59%，**VALUBusy 67.1%**（4 launch 28.2ms，7.05ms/次）；事件计时 7.56/7.79/7.74 TMAC/s = 峰 21.52 的 **36%**。VALU 忙而 dp4a 只 36% ⇒ 时间花在辅助指令。
- **R61 → DONE**；**R60（stream-k）→ DONE_NEG**（67.1% ≥ 40% 门，瓶颈是指令不是 in-flight bytes）。W923 的 50-65% 预判方向对、数值低估。
- **R63 → DONE_NEG**：该 kernel 3,411 条指令，dot 30.0%/地址 19.7%/缩放 13.1%/LDS 10.6%/解包 8.4%/同步 6.0%；`v_readlane`/`v_readfirstlane` 全在 top-25 外（≤0.4%）、`s_load_dword` 仅 2 条 ⇒ readfirstlane 无可消项；`global_load` 40 + `ds_read2_b32` 304 已是目标形态。
- **R84 改判 → DONE_NEG（重要）**：W942 初稿的 53.3% 分母是**整个 mmq-instance 模块**（多 J/fallback 求和），真 kernel 里 dot4 只占 **30.0%** ⇒ 减半 = 总指令 −15% ⇒ kernel −10.1%（VALU 67.1%）⇒ × gate/up 20.4% = 端到端 **−2.05%**（乐观 −2.4%）< 门 3.2% ⇒ 不做；R74 挂起。**新分母纪律**：组件占比必须用「实际 dispatch 的 kernel」作分母，模块/实例库求和只能当上界的上界。
- **结论**：MMQ 五扇门（R51/R58/R60/R63/R84）全关 ⇒ prefill 800→850 只剩 **R46（attn 拆三段→效率）/ R64（Q·K int8）**，这就是 R85 的全部空间。
- 外证：Qwen 官方 QSA 设计（12 层 QSA/48 层、indexer 4Q+1KV、budget 2048 = 512 block×4 token、1M 上下文 kernel 级 7.6× prefill）与 W887 的 604 MFLOP/token 一致。
- 账本：169 条 / 已结 104 = 61.5%；主线 141 / 104 = 73.8%；死块 0/28。
