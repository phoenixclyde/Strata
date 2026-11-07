import io

P = "deploy/PROGRESS.tsv"
row = ("B1参数轴", "P486",
       "A/B 协议的隐形偏差：**同一臂内 pass2 比 pass1 快 3.7%（2.5K）**，与是否重启无关（不重启的 ctl 也是 −3.70%）；16K 无此效应；8K 只在偶发窗口出现 6.65% 的双峰事件",
       "W1039", "count", "1", "1", "DONE",
       "**数据（本轮已有 8 对 arm 文件，逐对同 target 比 pass1 vs pass2）**："
       "2.5K：ctl **−3.70%**、dp4a −3.44%、dpp −4.43% ⇒ 中位 **−3.70%（负=pass1 更慢）**；"
       "8K：ctl −0.56%、dpp −0.31%、dp4a **−6.65%**；16K：+0.03 / +0.09 / −0.31。"
       "**读法一（协议影响）**：2.5K 的系统性 3.7% 是热身的，不是重启的——`ctl` 那一对**中间没有重启**，照样 −3.70%。所以**A/B 两臂的 pass 位置必须对称**：单 pass 窗口里每臂都是 pass1（如 A0 窗口 ctl/b/c）⇒ 偏差抵消；若一臂 1 pass、另一臂 2 pass，2.5K 上会凭空出现 3.7%。**本轮新窗口改成每臂 2 pass，正是为这个。**"
       "**读法二（8K 那个 6.65%）**：同臂同二进制、只差一次重跑，8K 就差了 6.65%（1339.1→1250.1），而中位只有 −0.31% ⇒ 这是**偶发的双峰事件**（约 1/6 概率），与 `generate.cpp` 注释里 R9700 的「queue placement 双峰」同形。"
       "⇒ **`STRATA_HIP_QUEUE_PRIME` 不该按「无现象」关掉，而应改判为「罕见但 5–7% 的双峰」**，等有窗口搭车时用 `=nn` 测（候选 `hipk` 已备）。"
       "**方法论落账**：以后任何 A/B 报告必须写「每臂几次 pass」，因为 pass 位置本身就是一个 3.7% 的效应量。",
       "P483;P482", "KW:pass2|3.70|双峰事件")
lines = io.open(P, encoding="utf-8").read().splitlines()
assert len(row) == 11
lines.append("\t".join(row))
io.open(P, "w", encoding="utf-8", newline="\n").write("\n".join(lines) + "\n")
print("appended P486")

PL = "deploy/W832_OPT_PLAN_V2.md"
p = io.open(PL, encoding="utf-8").read()
p = p.replace("**428 条 / 已结 341 / 79.7%**", "**429 条 / 已结 342 / 79.7%**", 1)
a = "- **判决**：`STRATA_MTP_HIP_PRIO` 天花板 5.1%（现实 2–6%）⇒ **不单独开窗**（`P483`）；`STRATA_HIP_QUEUE_PRIME` 无系统首请求惩罚（中位 +0.23%，`P483`），且 warm-up 会吸掉重启落位 ⇒ 降级。"
b = """- **判决**：`STRATA_MTP_HIP_PRIO` 天花板 5.1%（现实 2–6%）⇒ **不单独开窗**（`P483`）。`STRATA_HIP_QUEUE_PRIME` **改判**：无系统首请求惩罚，但 8K 上存在**偶发 6.65% 的双峰事件**（同臂同二进制、只差重跑），与 R9700 的 queue placement 同形 ⇒ 保留为「搭车测」（`P486`）。
- **A/B 协议（`P486`，对所有窗口生效）**：同臂 pass2 比 pass1 快 **3.7%@2.5K**（不重启的 ctl 也是），16K 无此效应 ⇒ **每臂 pass 数必须对称**；报告必须写明每臂几次 pass。"""
assert a in p
p = p.replace(a, b, 1)
io.open(PL, "w", encoding="utf-8", newline="\n").write(p)
print("plan: denom + P486 协议")
