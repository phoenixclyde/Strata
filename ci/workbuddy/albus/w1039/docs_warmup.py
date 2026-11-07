import io

R = "albus/w1039/reply.md"
r = io.open(R, encoding="utf-8").read()

old4 = "**428 条 / 已结 341 / 79.7%**（本轮 +41：`P445`–`P485`）"
new4 = "**429 条 / 已结 342 / 79.7%**（本轮 +42：`P445`–`P486`）"
assert old4 in r
r = r.replace(old4, new4, 1)

section = """
**27. 顺手抓到一个比目标更值钱的东西：`pass2` 比 `pass1` 快 3.7%，和重启无关（`P486`）**

为了不让窗口「开完才发现判不了（n=2 时 2×CV 17%）」，我把 collector 改成每臂两轮，并先用**现有 8 对 arm 文件**做了一次试跑。试跑立刻暴露两件事：

| target | ctl（中间**没有**重启） | dp4a | dpp |
|---|---|---|---|
| 2.5K | **−3.70%** | −3.44% | −4.43% |
| 8K | −0.56% | **−6.65%** | −0.31% |
| 16K | +0.03% | +0.09% | −0.31% |

（负 = `pass1` 更慢）

**第一件事：2.5K 的系统性 3.7% 是「热身」，不是「重启」。** `ctl` 那一对中间根本没有重启，照样 −3.70%。所以**A/B 两臂的 pass 位置必须对称**：单 pass 窗口里每臂都是 pass1（像 A0 窗口的 ctl/b/c），偏差抵消；若一臂 1 pass、另一臂 2 pass，2.5K 上会凭空长出 3.7% 的假差异。**新窗口改成每臂 2 pass，正是为这个**——这条要写进所有后续窗口的协议里。

**第二件事：8K 那个 6.65% 是偶发双峰。** 同臂、同二进制，只差一次重跑，8K 就从 1339.1 掉到 1250.1，而中位只有 −0.31% ⇒ 约 1/6 概率命中的双峰事件，和 `generate.cpp` 注释里 R9700 的「queue placement 双峰」（一半启动把两条忙队列排到同一 pipe，4K 提示慢 13%）**同形**。

⇒ 我把 `STRATA_HIP_QUEUE_PRIME` 的判决**改判**：不是「无现象，关掉」，而是「**罕见但 5–7% 的双峰**，等窗口搭车时用 `=nn` 测」（候选 `hipk` 已备，默认不变）。

**这也回头解释了以前那些 +2% 的怪数**：它们大多出现在「某臂的第 1 pass 对上另一臂的第 2 pass」这种不对称里，而当时我们把 2.5K 的 +2% 一律写成「首条冷启动」。现在有数了：**3.7%**，而且它跟重启无关。
"""
r = r.rstrip() + "\n" + section + "\n"
r = r.replace("`decode_split.py` / `decode_timing.txt`。",
              "`decode_split.py` / `decode_timing.txt` / `warmup_effect.py` / `summarize_kvg.py`。", 1)
io.open(R, "w", encoding="utf-8", newline="\n").write(r)
print("report §27 added; §四 ->", new4)

M = ".workbuddy/memory/2026-11-07.md"
add = """
### W1039 / P486（14:0x）A/B 隐形偏差：pass2 比 pass1 快 3.7%，与重启无关

- 8 对 arm 文件逐对比：2.5K ctl **−3.70%** / dp4a −3.44% / dpp −4.43%（负=pass1 慢）；8K −0.56 / **−6.65** / −0.31；16K ≈0。
- `ctl` 那一对中间**没有重启**也 −3.70% ⇒ 是**热身**不是重启。⇒ **每臂 pass 数必须对称**；报告必须写「每臂几次 pass」，因为 pass 位置本身是 3.7% 的效应量。
- 8K 的 6.65% 是同臂同二进制只差重跑的**偶发双峰**（约 1/6），与 R9700 queue placement 同形 ⇒ `STRATA_HIP_QUEUE_PRIME` 由「无现象」**改判为「罕见 5–7% 双峰」**，等窗口搭车测（候选 hipk 已备）。
- 回头解释了历史里那些「2.5K +2%」：多为 pass 位置不对称，当时一律记成「首条冷启动」。
"""
io.open(M, "a", encoding="utf-8", newline="\n").write(add)
print("memory appended")
