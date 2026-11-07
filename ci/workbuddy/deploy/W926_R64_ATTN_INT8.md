# W926 · R64：attention int8 点积 —— 实测推翻"O(L²) 假设"，且 k8v4 挡住 dp4a

> **【AUDIT24 P1 · 2026-11-04】三处更正**：①§45 写「占比稳定在 15–19%」，同段实测却是
> 8K **14.8%** / 32K **15.3%** / 99K **15.3%** —— 上界 19% 无出处，应写 **14.8–15.3%**；
> ②§81「最好情况 4–6%」与 §90「3.4–4.3%」自相矛盾，以可复算的 **3.4–4.3%** 为准；
> ③§41 的机制「稀疏 ⇒ O(L×k)」被 `W946` 修正为「每 token 仍扫 2048 个 cell 的候选，再按 `ids` gather」，
> `R89` 已按纪律⑱重开（源码阅读不足以结题）。

日期：2026-11-04 00:2x – 01:3x
状态：**DONE_NEG**（技术前提部分不成立；上限仅 4.0% 刚过噪声门，但需改 Q 量化 → 精度风险）。**注（`AUDIT24`）**：占比段应写 **14.8–15.3%**（不是 15–19%），上限段以 **3.4–4.3%** 为准；`R64` 仍 OPEN（窄化为只做 Q·K）
副产品：**QSA 稀疏使 attention 占比不随长度增长**（推翻常识假设）

---

## 1 先纠一个我自己的口径错

`W912`/`W924` 里我一直在说「attention 占 prefill 14.9%」，但日志里其实是两个字段：

```
strata prefill timing: 7885 tokens, GPU timeline 10536 ms, wall 10596 ms, host staging 1321 ms:
  embed+steps 3 (0.0%)  hc read 3 (0.0%)  gdn 1342 (12.7%)
  qsa proj 541 (5.1%)   qsa indexer 0 (0.0%)  qsa select 49 (0.5%)
  qsa attn 1557 (14.8%)                              <-- attention 主体在这里
  router+shared 321 (3.0%)  host grouping 51 (0.5%)  gather 32 (0.3%)  wait copy 48 (0.5%)
  dequant 593 (5.6%)  gemm gate/up 2190 (20.8%)  gemm down 1455 (13.8%)  ...
```

**`qsa proj` 只有 5.1%，`qsa attn` 是 14.8%**。之前抓 `qsa proj` 当 attention 是错的。

## 2 决定性实测：attention **不是 O(L²)**

日志里已有从 7.9K 到 99K 共 7 个长度的 `qsa attn` 绝对耗时（同一配置，可直接拟合）：

| tokens | qsa attn ms | 占 prefill |
|---|---|---|
| 7,929 | 1,568 | 14.8% |
| 8,378 | 1,674 | 13.6% |
| 21,822 | 6,905 | 15.5% |
| 28,873 | 8,352 | 18.6% |
| 28,906 | 8,375 | 19.6% |
| 31,633 | 10,152 | 15.3% |
| **99,382** | **32,876** | **15.3%** |

拟合：长度涨 **12.5×**，时间只涨 **21.0×** ⇒ 指数 **1.20**，**远不是 2.0**。
对照 `qsa proj`（本应 O(L)）：指数 **1.22** —— **两者同阶**。

**原因**：QSA 是**稀疏注意力**（先 top-k 选 KV 再算），所以 attention 的成本 ≈ O(L × k)，k 固定
⇒ 与 proj 同阶。`qsa select`（top-k 选择本身）只占 **0.5%**，说明选择做得很快。

**⇒ 常识假设「长上下文 attention 会成为主战场」在本引擎上不成立**：
8K 是 14.8%，32K 是 15.3%，**99K 还是 15.3%**。占比稳定在 **15–19%**。

## 3 技术前提：`--kv k8v4` 让 V 无法 dp4a

源码分支（`qsa_prompt_attn.cu:2431`）：

```cpp
if (pools.k_q != nullptr && pools.v_q4 != nullptr) {   // hybrid K8V4: int8 K + dequantized-q4 V
    if (!pools.k_scale) return false;
    if (volta) return launch70<3>(...);
    return launch<3>(...);          // <-- 我们走这条（KV_MODE == 3）
}
```

`KV_MODE == 3` 的注释自己写着：`K as int8, V dequantized to fp16 (scale 1)`。
这个 TU 里 `ggml_cuda_dp4a|__dp4a|sdot4` 命中 **0** ⇒ 计算走 fp32/fp16 FMA。

而 ki 的 `fattn-q8.cuh` 之所以能用 `sdot4`，是因为它 **K 和 V 都是 Q8**（int8×int8）。
我们 **V 是 4-bit**，`v_dot4_i32_i8` 只接受 int8×int8，`v_dot8_i32_i4` 是 i4×i4（`W909` 实测过）
⇒ **V 这一半在现有 KV 格式下根本用不上任何 dot 指令**。

要 int8 化只有两条路，都不是"移植"而是"换格式"：
1. **改成 k8v8**（V 也 int8）→ KV 显存 +50%，精度重测；
2. V 保持 fp16 只把 Q·K 走 dp4a → **需要把 Q 量化成 int8**（现在是 `const float* q`），
   引入 Q 量化误差，属"改数值"。

## 4 Amdahl：上限刚过噪声门

`端到端上限 = attention 占比 15.5% × 点积占比 × 0.75（dp4a 把指令数降到 1/4）× prefill占端到端 73.1%`

| 点积占 attention | prefill 省 | TTFT | 端到端 |
|---|---|---|---|
| 40% | 4.65% | 4.65% | **3.40%** |
| 50% | 5.81% | 5.81% | **4.25%** |
| 70% | 8.14% | 8.14% | **5.95%** |

噪声门 `2×CV = 3.2%`。**最好情况也就 4–6%，而且这是"点积占一半以上 + 完全消除"的上限。**

对照 `R58` 的教训：`R51` 的解包理论上限 4.15%，实测 **−6~−10%**。**理论上限刚过门时，实测大概率是负的。**

## 5 判定：DONE_NEG

三条理由，任一条都够：

1. **技术前提部分不成立**：V 是 4-bit，dp4a 用不上；只剩 Q·K 可能，且要把 Q 量化（改数值）；
2. **上限不足**：端到端 3.4–4.3%，刚好压在噪声门 3.2% 上；
3. **代价不成比例**：要改内核 + 改 Q 量化（或改 KV 格式 k8v4→k8v8，显存 +50%），
   而 `R51` 的先例说明"理论上限刚过门"的改动实测往往为负。

**保留的观察**：如果将来把 KV 换成 **k8v8**（这是独立决策，牵涉显存与精度），
这一条要重估，因为那时 V 也能 dp4a，且 Q 量化误差可以与 K 的量化共用 scale。

## 6 副产品（值得单独记）

**`qsa attn` 的指数是 1.20，`qsa proj` 是 1.22** —— 这说明：
- QSA 的稀疏选择把 attention 从 O(L²) 压成了 O(L)；
- 所以**"长上下文靠优化 attention"这条通用经验在本引擎上无效**；
- 真正随长度涨的是 `gemm gate/up` + `gemm down`（8K 时合计 34.6%，且是 O(L) 但系数大）。

⇒ 后续若要攻长上下文，靶子应该是 **GEMM/dequant**，不是 attention。

## 7 复现命令

```bash
# 1) 阶段分解（每请求一行，常开，不需要 trace）
docker exec strata166-407 sh -c "grep -oE 'strata prefill timing: [0-9]+ tokens.*qsa attn [0-9]+ \([0-9.]+%\)' \
  /data/strata-huihui-ud-iq4_xs.log | sed -E 's/.*: ([0-9]+) tokens.*qsa attn ([0-9]+) \(([0-9.]+)%\).*/\1 \2 \3/' | sort -n -u"

# 2) 确认我们的 KV 分支
grep -n "v_q4 != nullptr" -A3 src/kernels/cuda/qsa_prompt_attn.cu

# 3) 确认这个 TU 里没有 dot 指令
grep -c "ggml_cuda_dp4a\|__dp4a\|sdot4" src/kernels/cuda/qsa_prompt_attn.cu   # -> 0
```
