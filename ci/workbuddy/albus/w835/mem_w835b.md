## W835b　上游侦察与三条修正（2026-10-31 14:5x）

- **机主批评成立**：§1–§8 只看 166 本地树。KI 本地 `6ccbb03`(09-27) vs 上游 `3857591d`(10-26)，
  **落后 1209 个 commit**（59 条 gfx906 提交）；llama.cpp 上游 `0ec4027a`(10-31)；Strata 我们已最新。
  ⇒ 规矩：**凡判定"能不能移植"，必须先拉上游 HEAD 再下结论**。
- **修正一（否掉自己上一轮的一条）**：KI `DEAD-ENDS.md` 有同名实验
  「dp4a/dot2/dot8 swap in the KQ loop」→ **DEAD-END**，理由 "dp4a already inner loop and FULL-RATE
  (4.44× fp32)；B=1 decode is gather-HBM-bound ~2.7×，so ALU swaps can't surface"。
  ⇒ **gather 型 kernel 换 ALU 指令无效**；我们的 GDN/QSA-score 是 dense GEMV，机理不同，但
  **必须先 roofline 判定，不能假设**。§5 的「各项 30-50% ⇒ −5~−10%」未区分 gather/dense，作废。
- **修正二（真杠杆在字节侧）**：KI `T1` **PROBE GO**——int8 W8A16 打**未量化的 BF16 权重**：
  lm_head **1.93×**（1717 µs vs 记录 floor 3114–3193）、其他 floor-bound **2.00–2.42×**，
  天花板 **dense +10–13% / MoE +14–19%**。
  我们对应的未量化约 **14 ms/窗口（31%）**：GDN z/out-proj/rec/ab 4.36、QSA q/attn/out-proj 4.05、
  router 3.84、head 1.73（专家读取与 HC 已量化，不在内）。
  **但同族的 `T-1` 最终 NOT PASS**（drafter fp16 mass："earlier +15–18% was a cold-start misread"）
  ⇒ **probe GO ≠ serving GO**，必须过 serving gate。
- **修正三（同模型 ISA 底账）**：KI 服务的**就是 Qwen3.8-Flash-Next / qwen4_exp QSA**。
  每 32 MAC 的指令数：fp16 **32**（`v_dot2_f32_f16`）／bf16 **60**（标量 `v_fmac_f32`，无 bf16 指令）／
  int8 **16**（`v_dot4_i32_i8`）。实测 **QSA kernel pair：fp16 26.5 ms vs bf16 116.5 ms = 3.9×**。
  ⇒ 我们已走 fp16（`HIP_PROMPT_F16=1`），**这 3.9× 已吃到**；任何把 QSA 推向 bf16 的改动都是灾难。
  `tiled indexer`：fp16 **1.39×**、bf16 **0.42×**，须 dtype 门控 ⇒ 我们的 `native_qsa_indexer.cu` 待对照。
  `int8 KV`：gfx906 上 **attention prefill 慢 2.5–2.7×、decode 中性**，只买容量 ⇒ **我们 `--kv k8v4` 要核对代价**。
- **llama.cpp 定位**：`#15927` **已合并**（SRAM 8/16B reads + AMD FP16 dot，作者原话
  「v_dot2_f32_f16 available everywhere except for RDNA 1」——与我们的 llvm-mc 判定一致）；
  `#16291` **closed 未合并**（bpermute→swizzle，gfx906 **+20%**），与我们的
  `STRATA_GFX906_ATTN_QUERY_SWIZZLE` 是同一件事 ⇒ **双向确认，这条路是对的**。
  ⇒ llama.cpp 与 Strata 是**平行实现，只共享手法**。
- **Strata 上游顺带发现**：`#3986` 与 `#4766` 两个 open PR 都在修 dflash2 在 gfx906 的构建（**= 我们的 W776，撞车**）；
  `#3073` `SELECT_SIMT=2` 是新取值未测；`#4781` 报 0.1.54 prompt rate 回归且指向 auto expert cache。
- **新顺序**：roofline 先行（不停服 40 min）→ T1 同型探针 → indexer tiled 对照 → kv k8v4 prefill 代价。
- **KI 的三条方法学**（与我们踩的坑逐条对应）：standalone 赢不迁移 serving；serving graph A/B 才是 µs 级 gate；
  PPL 在 hybrid attention 上不可靠，要文本连贯 + logprob 并看。
- 文档 `deploy/W835_GFX906_PORT_FEASIBILITY.md` §9；登记 **P219（CORRECTED）/ P220（CONFIRMED）**，221 行。生产未动。
