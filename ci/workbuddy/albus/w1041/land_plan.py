#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""W1041: §0.1 (denominator + queue) + the §6.5 回写 block + its directory row."""
import io, os, re, shutil, time

ROOT = r"D:/workbuddy_space/strata_ws"
PLAN = os.path.join(ROOT, "deploy", "W832_OPT_PLAN_V2.md")
s = io.open(PLAN, encoding="utf-8").read()
shutil.copy2(PLAN, PLAN + ".bak_w1041_" + time.strftime("%Y%m%d_%H%M%S"))

s = re.sub(r"\| 进度分母 \| \*\*\d+ 条 / 已结 \d+ / [\d.]+%\*\*（W1040；",
           "| 进度分母 | **443 条 / 已结 354 / 79.9%**（W1041；", s, count=1)

OLD_Q = "| **唯一队列** | **R104 已结（W1040 装机："
NEW_Q = ("| **唯一队列** | **R103 重开并结、待移植（W1041 `P498`：用 R104 的取样面把 attn 一支从「不可测」改判为"
         "「数值代价优于现役 KV 档」，attn −10.2…−11.4%、整条 −1.0…−2.3%；移植到 `pr/k10` 后补任务级门 + 生产 A/B）** → "
         "**R104 已结（W1040 装机：")
assert s.count(OLD_Q) == 1, s.count(OLD_Q)
s = s.replace(OLD_Q, NEW_Q)

BLOCK = """
---

### 回写 · W1041（2026-11-07 14:32–14:41）R103 重开：换掉那把量尺，DP4A 从「不可测」变成「比现役 KV 档还便宜」

> 停机 **549 s**（四臂窗口 381 s + 补 D 臂 168 s），两次停/起，**零装机**；生产仍是 `kvg`（`a85743d7`）+ config `ee69ebc2`。

- **重开的理由不是翻案，是换尺**：`P467` 把 attn 一支结案成「现有数值门不可测」——七组两两 KL 全在 0.0354–0.0465，探针却证明读法/算术只差 1e-6 ⇒ 当时判的是门，不是改动。R104 交出来的替代取样面是 `STRATA_DUMP_FIRST_LOGITS` 的 **fp32 全词表 logits**：能逐字节比，也能算概率加权的差。
- **同一对臂，两把尺差一个量级**：C（`pa5`+`ATTN_DP4A`）vs A（`b12180`）在旧门里读 **0.04**，在新取样面的 8K 上是 **0.00345**。⇒ 旧门的绝对值不能跨仪器引用；0.0139 这个阈值只对那台仪器成立。
- **四臂（全部同参、`--expert-cache 1500` 实得 1915 槽）**：A=`b12180` / B=`pa5` 无开关 / C=`pa5`+`DP4A` / D=`b12180`+`--kv fp16`。**B≡A 四个长度逐字节相同**（build floor 干净），所以 C 的差异里没有「换了棵树」的成分。
- **数值（相对 A 的 KL，nats）**：C = `0.00037 / 0.00345 / 0.01429 / 0.18750`，D = `0.00155 / 0.01113 / 0.01699 / 0.38387`（1K/8K/16K/20K）。**C 四段全部优于 D**（4.2× / 3.2× / 1.19× / 2.05×）。D 是「把 KV 存成 fp16」的同性质改动，而我们为了省显存一直用更省的 k8v4 ⇒ **C 的代价小于我们已经接受的那一档**。这就是「自带锚」的意义：不引用别人的 0.0139 或 0.05，直接拿自己的现役档当预算线。
- **性能同一次 run 里就有**：`qsa attn` C vs B = 66/1404/3050/3914 ms vs 74/1585/3424/4359 ⇒ **−10.2…−11.4%**；整条 5440→5384 / 10635→10394 / 21622→21211 / 30722→30338 ⇒ **−1.0…−2.3%**（复现 `P452`）。
- **我预注册的第一指标是错的（自我更正）**：`max|Δlogit|` 在 C/D 上都是 3.3–4.8 nats，而 KL 只有 0.0004–0.19——因为极值落在概率质量几乎为零的尾部 token。**决策量必须概率加权**（KL / top-64 KL / top-10 重合），max|Δ| 只能当病态报警器。与 `P485`（中位数不可除）、`P493`（取样面错）同族：**先定对量的定义，再谈阈值**。
- **预注册的 top-1 条件没达标，写明不略过**：20000 那点 C 与 D **都翻了 argmax**，而该点参考分布本身是近掷硬币（p(top1)=0.683、top1−top2 裕度 0.42、熵 0.83 nats）；1K/8K/16K 两臂都保持 argmax。⇒ 单点翻面不足以下质量结论，但字面判据是不达标。**装机前补任务级门**（R104 用过的 28,695 token needle + 16K 档），外部实测也正好支持这条：perplexity 平、KL 均值 <0.01 时答案翻转率仍可到 5%。
- **下一步（不是本轮）**：移植**不是 cherry-pick**——`port-all` 的 `qsa_decode_attn.cu` 与 `pr/k10` 已明显分叉（DPP 模板、dp4a 头、warp-per-group 量化整段），要真合并；然后在 `kvg` 树上建 `kvg+dp4a` 候选，**先用本轮同一取样面验 floor**（`kvg` 无开关 ≡ `kvg`），再任务级门、生产 A/B、装机。**生产源码树本轮未动**（`pr/k10 @ af797b90`，脏 0 行）。
"""

DIR_ROW = ("| `回写 · W1041（2026-11-07 14:32–14:41）R103 重开：换掉那把量尺，DP4A 从「不可测」变成「比现役 KV 档还便宜」` | "
           "四臂（build floor 逐字节相同）+ 锚臂（fp16 KV）：DP4A 的 KL 四段全优于锚，attn −10.2…−11.4%；"
           "预注册的 max|Δlogit| 被证明是错的第一指标；top-1 在 20K 未达标 ⇒ 装机前补任务级门 |")

i0 = s.index("### 6.5.0 回写块目录")
t0 = s.index("| 小节 |", i0)
tend = s.find("> **【AUDIT27", t0)
tend = tend if tend > 0 else t0 + 60000
last = s.rfind("| `回写 ·", t0, tend)
i1 = s.index("\n", last) + 1
s = s[:i1] + DIR_ROW + "\n" + s[i1:]
assert s.count(DIR_ROW) == 1

s = s.rstrip("\n") + "\n" + BLOCK
io.open(PLAN, "w", encoding="utf-8", newline="\n").write(s)
print("plan updated", os.path.getsize(PLAN))
