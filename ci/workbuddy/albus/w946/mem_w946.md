
## W946 · gfx906 项目全景（8 家）：找到同模型同卡的那家（16:0x）
- **核心发现**：`sixvolts/llamacpp-gfx906-furnace`（upstream e6ab7c1a4 2026-09-22，11-02 更新）跑**同一个 177B MoE / UD-Q4_K_XL / 4×MI50**：prefill 8K **887→1251**、32K **867→1561**、llama-bench pp8192 **877→1978（+126%，异步分阶段拷贝）**、QSA sparse @48K **622→1150（+85%）**、单 MI50 27B pp512 **216→325（+50%，全类型三平面 repack 组合）**。
- **版本差**：我们 llama.cpp **0.4.1**，社区最新 **v0.7.0**（exabit merge-v0.7.0，2026-10-22）⇒ 差 3 个 minor，三个月上游对 qwen4exp/GDN/QSA 的修正一条没吃。
- **重排权重**：指令层（R51/R58/R60/R63/R84）最低；**拷贝/调度层（R88）> 布局层（R86 repack）> attn 效率（R46）**。
- **R89 当场判否（A 级源码）**：`qsa_prompt_attn.cu:131` `n=steps[…]`、`:133` `ids += qi*cap`、`:193` `cell = ids[c0+c]` 经 page_table ⇒ **我们早已 gather-only**，furnace 的 +85% 不成立；W926 的 1.20 指数 = indexer O(n) + core O(2048)。
- **新条目 R88**：prompt 路径异步分阶段拷贝；本机 wait copy 8.9-12.7% ⇒ 端到端上限 12.7%（不是 126%）。
- **两处矛盾已记**：①furnace +50% 是全类型组合，Q4_K 单项仍可能是 mx 的 +2~5%；②furnace「58%→89% HBM」是 decode matvec（M=1），与本机 prefill MMU `MemUnitStalled 0.36%` 不矛盾。
- **构建口径**：mixa 的 Strata 与 llama.cpp 两套镜像都用 `-mllvm -amdgpu-sched-strategy=max-ilp`（= R49）。
- 账本：173 条 / 已结 105 = 60.7%；主线 145 / 105 = 72.4%。
- **方法教训**：搜关键词要找「同题的人」（模型名 + 量化 + 卡数），不是「同领域的人」（MMQ/gfx906/kernel）。
