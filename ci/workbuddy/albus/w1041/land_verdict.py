#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""W1041: land the R103 verdict (P498), close P497, and self-correct the metric choice."""
import io

P = r"D:/workbuddy_space/strata_ws/deploy/PROGRESS.tsv"

NOTE = (
 "**W1041 实测（窗口 14:32:01–14:38:22 四臂 + 14:38:43–14:41:31 补 D；共停机 549 s、两次停/起、零装机）**。"
 "**取样面 = R104 的**：`STRATA_DUMP_FIRST_LOGITS` float32 全词表（993,280 B/个）、四个长度 1000/8000/16000/20000、"
 "四臂同参（`--expert-cache 1500` 实得 1915 槽、`--kv` 见各臂）。"
 "**① build floor**：B（`pa5` 无开关）与 A（`b12180`）**四个长度全部逐字节相同**（`cmp -s` IDENT）⇒ 后面 C 的差异里没有 build 成分。"
 "**② 判决数据（相对 A 的 KL，nats）**：C（`pa5`+`ATTN_DP4A`）= **0.00037 / 0.00345 / 0.01429 / 0.18750**；"
 "D（`b12180` + `--kv fp16`，**锚**）= **0.00155 / 0.01113 / 0.01699 / 0.38387**。"
 "**C 在四个长度上全部优于 D**（好 4.2× / 3.2× / 1.19× / 2.05×）——而 D 这一档是「把 KV 存成 fp16」的同性质改动，"
 "我们**为了省显存一直在用更省的 k8v4**，也就是说 C 的数值代价**小于我们已经接受的那一档**。"
 "**③ 性能（同一次 run 的 prefill 计时，单 pass）**：C vs B 的 `qsa attn` = 66/1404/3050/3914 ms vs 74/1585/3424/4359 ms ⇒ "
 "**−10.2…−11.4%**；整条 GPU timeline 5440→5384 / 10635→10394 / 21622→21211 / 30722→30338 ⇒ **−1.0…−2.3%**（复现 `P452` 的 −11.3% / −1.78%）。"
 "**④ 预注册的 top-1 硬条件没满足，必须写明**：20000 那点 C 与 D **都翻了 argmax**；而该点的参考分布本身是个近掷硬币"
 "（p(top1)=0.683、top1−top2 裕度 0.42、熵 0.83 nats），1K/8K/16K 三点两臂都保持 argmax ⇒ 单点翻面在近掷硬币处不构成质量证据，"
 "但**按预注册的字面判据它就是不达标**，不许悄悄略过。**处置**：装机前补一道**任务级门**（R104 用过的 28,695 token needle + 16K 档），"
 "不再用「一个位置的 argmax」当质量结论——外部实测也正好说这件事：perplexity 平、KL 均值 <0.01 时，答案翻转率仍可到 5%（technolynx 2026）。"
 "**⑤ 方法自我更正（重要）**：我预注册的第一指标是 `max|Δlogit|`，实测显示它是**错的第一指标**——C/D 的 max|Δlogit| 都在 3.3–4.8 nats，"
 "而同期 KL 只有 0.0004–0.19，因为极值落在**概率质量几乎为零的尾部 token**上。**决策量必须是概率加权的**（KL / top-64 KL / top-10 重合），"
 "max|Δ| 只能当「有没有出现病态大偏差」的报警器。这条与 `P485`（中位数不可除）、`P493`（取样面错）同族：**先把量的定义定对，再谈阈值**。"
 "**⑥ 与旧结论的关系**：`P467` 判「现有数值门不可测」是对的——同一对臂（C vs A）在旧门里读 0.04，在新取样面上 8K 只有 **0.0034**，差一个量级。"
 "**⇒ R103 的 attn 一支不再是「不可测」，而是「用对尺子后可以判」，且判决是「值得采纳」。**"
 "**⑦ 下一步（不是本轮）**：移植不是 cherry-pick——`port-all` 的 `qsa_decode_attn.cu` 与 `pr/k10` 的已明显分叉（DPP 模板、dp4a 头、"
 "warp-per-group 量化整段），要真合并；建 `kvg+dp4a` 候选 → 先用本轮同一取样面验 floor（`kvg` 无开关 ≡ `kvg`）→ 任务级门 → 生产 A/B → 装机。"
)

row = ["B5本机缺口", "P498",
       "**R103 attn 一支结案（改判）：DP4A 的数值代价比我们已经在跑的 KV 档更小**（四长度 KL 全优），"
       "attn −10.2…−11.4%、整条 −1.0…−2.3%；但预注册的 top-1 条件在 20K 未达标 ⇒ 装机前须补任务级门",
       "W1041", "count", "1", "1", "DONE", NOTE, "P497;P452;P467",
       "KW:ATTN_DP4A|锚|0.00345"]

lines = io.open(P, encoding="utf-8").read().splitlines()
assert not any(l.split("\t")[1] == "P498" for l in lines if l.count("\t") >= 9)
assert len(row) == 11 and all("\t" not in x for x in row)

out, hit = [], 0
for l in lines:
    f = l.split("\t")
    if len(f) >= 10 and f[1] == "P497":
        f[6], f[7] = "1", "DONE"
        f[8] = f[8] + " **结果见 `P498`。**"
        hit += 1
        l = "\t".join(f)
    out.append(l)
assert hit == 1
out.append("\t".join(row))
io.open(P, "w", encoding="utf-8", newline="\n").write("\n".join(out) + "\n")

tot = done = 0
for l in io.open(P, encoding="utf-8"):
    f = l.rstrip("\n").split("\t")
    if len(f) >= 10 and f[0] != "block" and not l.startswith("#"):
        try:
            tot += int(f[5]); done += int(f[6])
        except ValueError:
            pass
print("totals", tot, done, round(100.0 * done / tot, 1))
