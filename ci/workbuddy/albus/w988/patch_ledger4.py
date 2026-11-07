# -*- coding: utf-8 -*-
import io, time
TS = time.strftime("%Y-%m-%d %H:%M")

P = "D:/workbuddy_space/strata_ws/deploy/PROGRESS.tsv"
lines = io.open(P, encoding="utf-8").read().splitlines()
out = []
for l in lines:
    c = l.split("\t")
    if len(c) < 8:
        out.append(l); continue
    if c[1] == "R93":
        c[8] = (c[8] or "") + (
            " 【W988 补第二臂 %s】**chunk 32768 vs 16384**：2K 507.82/511.73（−0.76%%，band 2.00%%）、"
            "8K 705.16/704.32（+0.12%%）、16K 777.12/774.74（+0.31%%，band 0.32%%）⇒ 不显著、自动回退。"
            "**三值齐**：8192 在 16K −5.75%%（判否）、32768 中性、**16384 正确**。" % TS)
        l = "\t".join(c)
    elif c[1] == "R90":
        c[7] = "PARTIAL"
        c[8] = (c[8] or "") + (
            " 【W988 降级 %s】机主追问后复核：**R90 的验收含「质量对金标 KL/top-1」，这一半从未跑**"
            "（W960 只做了性能六档 A/B，W962/W966 是内核等价性，W957/W958 的逐位判据已作废）。"
            "⇒ 状态 DONE 改为 **PARTIAL**，缺的质量门另立 **R94**。" % TS)
        l = "\t".join(c)
    out.append(l)

rows = [
    "\t".join(["B5本机缺口", "R94", "v0.9.0 基线的质量门：对金标 KL / top-1（先测地板，再比 0.4.1）", "W988", "count", "1", "0",
               "OPEN",
               "**W988 立（%s，机主「测完有实际数据才能做判断」）**：R90 结案时只验了性能，质量门被跳过。"
               "做法：①先测本引擎的自一致地板（同 prompt 重复跑，量化 run 间抖动，W958 已证 run 间不逐位）；"
               "②再对金标算 KL 与 top-1 一致率；③判据沿用 MEMORY 的标尺（提示侧 KL ≤0.0139、top-1 ≥99%% 量级），"
               "不达标则 v0.9.0 基线降回参考实现。" % TS]),
    "\t".join(["B1参数轴", "P264", "`--prefill 32768`（R93 的第三个 chunk 值）", "W988", "count", "1", "1", "DONE_NEG",
               "**W988（%s）** n=3/长度：2K −0.76%%、8K +0.12%%、16K +0.31%%（band 0.32%%）⇒ 不显著，回退；16384 维持。" % TS]),
]
io.open(P, "w", encoding="utf-8", newline="").write("\n".join(out + rows) + "\n")
print("PROGRESS: R93 补臂、R90→PARTIAL、+R94/P264")

Q = "D:/workbuddy_space/strata_ws/deploy/params/PARAM_REGISTER.tsv"
rl = io.open(Q, encoding="utf-8").read().splitlines()
head, body = rl[0], rl[1:]
o2 = []
for l in body:
    c = l.split("\t")
    if c and c[0] == "P99":
        c[10] = (c[10] if len(c) > 10 else "") + (" 【W988 机主确认 %s】`--vision` **要用，保留**（不删）。" % TS)
        l = "\t".join(c)
    o2.append(l)
io.open(Q, "w", encoding="utf-8", newline="").write("\n".join([head] + o2) + "\n")
print("REGISTER: P99 记录机主确认保留")
