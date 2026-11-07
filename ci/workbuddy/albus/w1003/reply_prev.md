**四件套**

| 项 | 状态 |
|---|---|
| 生产容器 | `4f387a12e84b` / `strata-gfx906:0.2.10-101`，health ok，引擎 md5 `eea5ea37…`、config `e62685e6…` **本轮零改动零重启** |
| 主线 | W1003：宽度×类型×形状三臂扫描，推翻 W999/W1001 的两个前提 |
| 本次落生产 | **无**（`src/` `include/` `CMakeLists.txt` 零改动）；落了证据 + 决策文档 + 门 |
| 进度 / 队列 | 209/131/62.7% 不变；`R97 解散`，队列转为 dequant / wait copy |

---

## 一、结论先行（三条，都是本轮实测）

1. **「320 行 repacked 慢 15%」不是 kernel 的锅，是分派规则的锅。** 同一点 w32 = **0.955**、w64 = 1.183；mx 的 `use_w32 = n_assign < 2*BN_ID*ne02`（16 专家 = 4096 行）恰好在那里翻到 64 宽。**所以 R97「按段混合分派」这个方案本身没有意义**——不需要分两段，固定 w32 即可。
2. **生产的 gate/up 全是 K-quant，而 K-quant 的 repack 是净亏损。** 这一点由 pack 清单直接证明，不由我推测：`native_experts.txt` 的列是 `layer gu_type d_type …`，gu = Q4_K(12)/Q5_K(13) @ `[1280, 2560]`，down = Q5_1(7)/Q8_0(8) @ `[2560, 640]`。而 **K=640 不是 QK_K=256 的倍数，K-quant 在 down 上几何上根本无法成立**——这正好解释了 Unsloth UD 为什么只在 gu 上用 K-quant。
3. **因此全量移植是 NO-GO，原因是测量结果证明它会变慢，而不是因为它难做。**

| 张量 | 类型 | w32 | w64 | 判 |
|---|---|---|---|---|
| gate/up | Q4_K | 2.26–2.98× | 1.02–3.87× | **永不 repack** |
| gate/up | Q5_K | 1.57–2.51× | 1.00–2.25× | **永不 repack** |
| down | Q5_1 | **0.79–0.81** | 0.93–2.28 | repack，w32 |
| down | Q8_0 | 0.54–0.69 | **0.58–0.61** | repack；≤320 行 w32，≥512 行 w64 |

端到端计算：down 占 prefill **13%**（W853 P104），−20% ⇒ **−2.6%**；Q8_0 层 −40% 但层数少 ⇒ **−2.6% ~ −3.3%**，低于预先定死的 **prefill@2K ≥5%**。

## 二、「完整移植」在我们引擎里到底是哪几段

我把「完整」定义成六条可执行、可机器检查的东西（完整版含 file:line 在 `docs/W1003_PORT_DECISION.md`）：

| 通道 | 落点 | 状态 |
|---|---|---|
| C1 权重上传 | arena 装载时一次性 repack，不进热路径。**Q5_1 down 尺寸中性**（1 228 800 = 1 228 800 B，`d_stride`/零尾/借槽账本全不动）；**Q8_0 down +2.3%**（1 740 800→1 781 760，唯一要改账本的地方） | 设计定稿，代码未动 |
| C2 调度分派 | `moe_mmq.cu:498 Context::run`：`expert_stride` 从 `expert_bytes/type_bytes` 换成 `repack_gcn_nbytes`；`Product` 加 `layout`，因为**同一层 gu 是 canonical、down 是 repacked** | NOT_STARTED |
| C3 激活对齐 | `quantize()` 已产出 grouped MMQ 布局；缺我们自己钉 `block_q8_1_mmq` 尺寸/偏移的断言 | PARTIAL |
| C4 融合 | **理由更正**：不是「prefill 无红利」，而是我们 gu 本来就是 `prefill.cpp:5300` 的**单次 1280 行调用**，上游 #29948/#31188 省的是第二次 launch，此处不存在 | N/A |
| C5 验收 | 逐位等价 + 六长度档 + 2×CV + KL/top-1 + `STRATA_REPACK_D` 灰度 + 镜像回滚 | NOT_STARTED |
| C6 混合分派 | **解散**：w32 在 down 全行数档都赢，没有「留给 canonical 的大段」 | NOT_APPLICABLE |

## 三、举一反三（你没问，但会影响你的判断）

- **mx 的 `use_w32` 阈值不能照抄**：它是为别的形状调的，照抄等于把上游的调参搬进我们的瓶颈（我们 32→1024 行 w32 全胜）。
- **上游 2026 的两笔 MoE 融合对我们无效**（#29948 稠密、#31188 MoE，DGX Spark +17.2% / 5090 +5.7%）：它们赚的是「两次 launch 合一次」，我们一次就是 1280 行。
- **真正的性价比排序没有变**：`dequant` 8–18% 与 `wait copy` 7–15% 都比 down 的 ~3% 大 3–5 倍，而且都是机制已经查清、不需要动 kernel 的活。

## 四、门的证据（不靠我口头声称）

- `ci/repack_ab/verify.py` 新增第 6 组：ratio 算术自洽、winner 必须是最快臂、四个生产组合必须齐、以及两条方向性断言（gu 必亏 / dn 必赚）。
- **负向自测 4/4 按预期 FAIL**：伪造 winner、篡改 ratio、删掉 `QK_K=256` 注释、删掉一个测点。
- `round_gate --ci` PASS；提交 `c43ffc98`（5 文件 +432/−12）已推；**GitHub Downstream gate run #26 completed/success @ c43ffc98**。
- 新增：`ci/repack_ab/WIDTH_SWEEP.tsv`（20 行实测）、`ci/repack_ab/type_sweep.cu`（入仓，不再放 /tmp）、`docs/W1003_PORT_DECISION.md`、`PORT_STATUS.md` 全面改写。

## 五、需要你裁一件事

按判据我**不建议现在开 down-only 这一轮工程**（~3% 换 C1/C2/C5 三条通道的改动与回滚风险）。两个选项：

- **A（我的建议）**：先把 `dequant` 与 `wait copy` 做完或判否，再回头收 down 的 3%；这两块合起来 15–33%，是 down 的 5–10 倍。
- **B**：你仍要「完整移植」这个动作本身落地，我就按 `docs/W1003_PORT_DECISION.md` 的 C1/C2 + C5 清单做 down 一路，全程 `STRATA_REPACK_D=1` 灰度、镜像可回滚，验收走六长度档 + 2×CV。

说 A 或 B 即可，B 我直接开工不再问。