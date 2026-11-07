
## 6. `#29953` 的特别说明（W1031 实测 + 上游原文）

`#29953`（MMQ 越界读修复）是本轮唯一「对我们有真实价值」的候选：它修的是 J 选得比宿主 padding 大 ⇒ kernel 读越过 src1 末尾。
但它的 PR 讨论里明确写着：验证覆盖 RTX PRO 6000 / 2080 Ti / RDNA3.5 / CPU 十种架构，
**"Still untested: MUSA, and AMD CDNA3/RDNA4/GCN hardware, which we only modelled."** —— **GCN 就是我们（gfx906）**。

实测吻合：ladder-5 臂（pin + 该条）在生产上回答退化（只有 reasoning、无答案）并触发客户端断连 ⇒ 判 REJECTED（臂不可信）。

要拿它，顺序必须是：

1. **CPU 规则检查**（不需要 GPU）：把 `mmq-config-gcn.cuh` 的 CASE 表读出来，按上游 `ggml_cuda_mul_mat_q` 的选 J 规则
   （tile 数最少、shared memory 装得下）复算我们每个生产形状（rows/expert、cols=2560 / 640 …）的 J，
   再对照 `src/prefill/moe_mmq.cu` 的 `pad512()` 与 dst 分配，判「kernel 的读/写范围是否被覆盖」；
2. 覆盖不足 ⇒ 先在粘合层补 padding（host 侧，不进 kernel），再用 `mmq_expert_bench` 离线计时 + 数值对齐；
3. 离线两项都过，才允许上生产做一次 A/B。

**禁止**像 ladder-5 那样直接装机 —— 那正是把 166 搞死的那一臂。

## 7. 现有臂的资产（W1031）

| 臂 | 树 | 二进制 | 结论 |
|---|---|---|---|
| pin（在产） | `ref/llama_3cf0325` | `strata-0.1.57-001` / `5e63174d` | 基线 |
| v0.9.0 | `ref/llama_b12110` + `src-v090` | `-004` / `e0edacb7` | prefill −3.8%，DONE_NEG |
| H1（回退 #31247） | `llama_v090_h1` | `-005` / `1f3d7d30` | 未恢复 ⇒ #31247 非元凶 |
| H2（pin 的 ggml-cuda） | `llama_h2` + `src-h2` | `-006` / `8bed7a20` | 回到基线 ⇒ 账在 MMQ 头 |
| #29478 单条 | `llama_pin_vsub4` | `build-vsub4` | 与 001 二进制逐字节相同 ⇒ 零 |
| ladder-5（#29953） | `llama_p5` | `-008` / `28a09fdc` | 回答退化 ⇒ REJECTED |
