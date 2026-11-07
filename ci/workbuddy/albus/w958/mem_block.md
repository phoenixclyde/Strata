## W958 · 确定性对照：逐位判据作废（18:4x–19:2x）

- 设计：一次停服跑 A1 / A2（同一 0.4.1 生产件）+ B1（0.8.0 移植版），同 prompt、同 args、加 `--dump-routing`。
- **结果**：**A1 vs A2 只有 7/64 个 token 相同（前缀 3）**；**B1 vs W957 的 B 是 64/64 全同**；A1 vs B1 也是 7/64。
  ⇒ `W957` 的"前缀 7"落在 A 自己的噪声里，**token 序列判据作废**；而且"更可复现"的是待升级的 0.8.0。
- **原因（源码写明）**：`generate.cpp:12706` —— 专家换入换出落在哪个窗口，决定该 token 用 CPU 还是 GPU 算，
  "which rounds differently from the CPU" ⇒ 不可复现。实测三次跑各换入 1436 / 576 / 1372 个专家。
- **待查假设**：① rocBLAS 运行期按计时选解（两臂日志都有 tuning enabled）；② 换入序列；③ 我们的适配恰好修掉某个竞争。
  测法：`--adapt-async 0` + 固定 rocBLAS 表 / `--rocblas-tuning 0`，先让 A 两次跑出 64/64。
- **判据改写**：升级验收 = 性能六长度档 A/B（`|Δ|≥2×CV`）+ 质量**对金标**的 KL/top-1（先测地板）；
  不能两臂互比 token。质量测量必须走 **serve + `STRATA_DUMP_FIRST_LOGITS`**（generate 的 native pack 不写 dump）。
- 台账 38/38；账本 176 条 / 已结 101（57.4%）；部署分支与生产仍未动，实验分支 `999b9121`。
