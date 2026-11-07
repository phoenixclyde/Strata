## W957 · R90-S4 第一轮：0.8.0 能跑，但不逐位（18:0x–18:5x）

- **方法纠错**：`--dump-logits` 在 native pack 上恒 0 字节（`generate.cpp:8760` 注释写明"native pack 从不走到 per-token dump 点"）；
  改用引擎打印的 `output : <ids>`（`--max-new 64 --top-k 1`）。
- **发现并修掉一个真 bug**：0.8.0 把 `mmq_args` 末尾的 `int64_t ncols_opt` 换成 **`int J_best`**，我们的位置初始化把
  `max_rows`(412) 塞进去 ⇒ `mul_mat_q_switch_J` 直接 `GGML_ABORT`（mmq.cuh:1594）。上游 `get_J_best` 是 `mmq.cu` 的 static，
  调不到 ⇒ 在 `fits()` 旁加 `pick_J()` 12 行（同一条 J 阶梯，取"tiles 最少且放得下"）。
- **两臂各 64 token，RC=0**：相同前缀 **7**，第 8 个 A=33413 / B=1666；prefill 604.8 vs 568.4 tok/s（单次、合成 prompt，不作判据）。
- **不构成"0.8.0 不行"**：还差**同二进制重复跑**的对照（`W899 §7.11` 记过引擎 run 间可能不确定）；判据也应从"逐位"
  改成"KL≤0.005 且 top-1≥99%，或 64 token 前缀 ≥48"（跨 4 个 minor 的升级要求逐位=要求升级不改数值）。
- 分支 `exp/R90-080` 提交 **999b9121**（6 文件 +59/−35），**未合**；部署分支仍 `55a1acd4` / tag r30 / 领先 39。
- 本轮停服 **4 次**（每次 ~4.5 min，脚本自动恢复），生产引擎与 config md5 未变。
- 台账 37/37；账本 176 条 / 已结 101（57.4%）。
