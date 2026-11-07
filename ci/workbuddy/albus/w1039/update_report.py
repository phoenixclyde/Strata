#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""W1039: fix the misplaced `## 正文`, refresh section 四, and append the two findings + the staged window."""
import io

P = "albus/w1039/reply.md"
s = io.open(P, encoding="utf-8").read()

# 1. `## 正文` landed above section 一 when the shape was restored; it belongs above the body's first block.
assert "---\n## 正文\n\n**一、生产容器" in s
s = s.replace("---\n## 正文\n\n**一、生产容器", "---\n\n**一、生产容器", 1)
assert "**1. pa3：怎么编的" in s
s = s.replace("**1. pa3：怎么编的", "## 正文\n\n**1. pa3：怎么编的", 1)

# 2. section 四 -- denominator from tools/progress.py (402 / 315 / 78.4%)
old4 = "**四、进度** — **399 条 / 已结 313 / 78.4%**（本轮 +12：`P445`–`P456`）。"
new4 = "**四、进度** — **402 条 / 已结 315 / 78.4%**（本轮 +15：`P445`–`P459`）。"
assert old4 in s
s = s.replace(old4, new4, 1)

# 3. H1: the claim that survived is narrower than the one in the old title.
oldh = "# W1039 — port-all 按 b12180 重编：pa3 可复现、pa4 抓到死代码、pa5 把 DP4A 从 +6.8% 救到 −11%——**但数值门判否，不装机**"
newh = "# W1039 报告 · pa3 可复现、pa4 抓到死代码、pa5 把 DP4A 从 +6.8% 救到 −11%；**而数值判决本身被一个归约混淆污染**"
assert oldh in s
s = s.replace(oldh, newh, 1)

# 4. the two findings + the staged window, appended before the 产物 block
anchor = "**产物**：`albus/w1039/reply.md`（本件）"
assert anchor in s
add = """**10. 先看「误差长什么样」：不是位宽，是共模（`P458`）**

fp16 那臂的 KL（0.03798）几乎等于 int8 那臂（0.04130），这本身就不该发生——fp16 的查询误差是 0.03%，
int8 是 1.3%，差一个数量级。所以先不猜机理，把四份已有 tsv 拿来做误差结构分析（零窗口）：

| 量 | int8 臂 | fp16 臂 |
|---|---|---|
| argmax 变化 | 322 / 4995 = **6.45%** | 285 / 4995 = **5.71%** |
| \\|Δlogp(target)\\| 中位 | **0.01769** | **0.01930** |
| \\|Δlogp\\| > 0.01 的比例 | **54.41%** | **55.22%** |
| \\|Δlogp\\| > 0.5 的比例 | 7.13% | 7.75% |

两臂的幅度分布**几乎重合**；逐点相关 **0.6965**（signed 0.5456），两臂同时 >0.001 的位置 **3247/4995**。
而地板臂（同二进制、两次独立容器）**逐位相同**（KL 0.00000 / top-1 100.00%）⇒ 共模不是环境噪声。
**若误差来自各自位宽的舍入，两条曲线应该差一个数量级；实测相等 ⇒ 有一个两者共有的结构差在主导。**
按这一条，`P454` 的机理（「int8 步长正好压在 0.19 nat 判决线上」）**撤回**——margin 数据仍有效
（322 个改动、234 个是「第一名掉到第二名」、间隔 p50 **0.191** nat），错的是我给的成因。

**11. 共模的来源：所有 OPT 臂跑的是另一个归约（`P457`）**

顺着「两条 OPT 路径共有、基线没有」这条线读派发，而不是继续猜算术：

- 生产 `env` 9 项里**没有** `STRATA_GFX906_ATTN_REDUCE12`（容器内 `grep -c` = 0），所以对照臂走
  `attn_chunk_kernel<M,false,true>`，**第 4 个模板实参 REDUCE12 = false**（12 次 `warp_sum`）；
- 而 OPT 臂的宏体是 `STRATA_ATTN_OPT_SWZ` → `attn_chunk_kernel<M,false,true,true,O>`，**REDUCE12 恒为 true**
  （12-in-16 打包归约，16 次 shuffle 顶 60 次）；
- 触发条件是 `if (const int opt_sw = gfx906_attn_opt(); opt_sw != 0)`，**与 `reduce12` 那个 env 无关**。

⇒ 到今天为止，每一个「开关 vs 对照」的数值门都同时换了**点积指令**和**归约方式**，两处一起变。
所以 `P453`（DP4A，KL 0.04130）与 `P456`（F16D，KL 0.03798）**不能归因到开关本身**——这也正好解释了
为什么两条完全不同的点积路径给出同一个误差量级。

**12. 下一步：先只改一个 env，不动二进制（`P459` 已备）**

最省的判别不需要重编：把 `STRATA_GFX906_ATTN_REDUCE12=1` 加到**生产二进制**上，对照臂就是它自己。

| 臂 | 二进制 | 只改这一项 | 读法 |
|---|---|---|---|
| A2 | `b12180` | 无 | 与 10:52 的 `g2_A.tsv` 对拍，验跨容器地板 |
| **R12** | `b12180` | `ATTN_REDUCE12=1` | **KL ≈ 0.038 ⇒ 归约是共因**；KL = 0 ⇒ 归约无辜 |

若 R12 是共因：DP4A / F16D 必须对**REDUCE12 版的对照**重测，`P447`/`P451`/`P456` 的判决作废重来；
若 R12 = 0：再开 phase 2，用 pa7 的两个诊断位继续剥——`CTLREAD=1`（基线算术、走 OPT 的手写 K 读法与末尾乘 scale，
KL 归零即证明读法无辜）与 `F16Q=1`（查询只做 fp16 往返、点积仍是 fp32 fma，把「q 精度」和「dot2 指令」拆开）。
pa7 = `f04b91a6ebcbc649449632c39e8fdf01` / **43,576,168 B** / 0 FAILED，`strings` 八项全在册（含新加的
`ATTN_CTLREAD` / `ATTN_F16Q`）；顺带把「bits 16/32 在没有 swizzle 时静默跑基线」改成打印一次警告。

"""
s = s.replace(anchor, add + anchor, 1)

# 5. artifacts line -- the new files
olda = "**原始数据**：166 上 `/home/albus/strata166/tmp/w1039/{arm_*,w2_*,w3_*}.json` 与 `window{,2,3}.log`。"
newa = ("**原始数据**：166 上 `/home/albus/strata166/tmp/w1039/{arm_*,w2_*,w3_*}.json` 与 `window{,2,3}.log`；"
        "数值门四份 tsv 与误差结构脚本在 `tmp/w1041/{run_A,run_B,g2_A,g2_Ab,g2_B}.tsv` + `error_structure.py`；"
        "本轮新增 `pa7_patch.py` / `build_pa7.sh` / `gate3.sh` / `gate4.sh`。")
assert olda in s
s = s.replace(olda, newa, 1)

io.open(P, "w", encoding="utf-8", newline="\n").write(s)
print("report updated: %d chars" % len(s))
